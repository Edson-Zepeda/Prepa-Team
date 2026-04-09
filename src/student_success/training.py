from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR

from .config import (
    ACTIONABLE_FEATURES,
    ADVICE_CATEGORICAL_FEATURES,
    ADVICE_FEATURES,
    ADVICE_NUMERIC_FEATURES,
    ARTIFACT_PATH,
    DATA_PATH,
    EXCLUDED_FROM_ADVICE,
    GOOD_PERFORMANCE_THRESHOLD,
    GOOD_PERFORMANCE_THRESHOLD_10,
    METADATA_PATH,
    MEXICAN_SCALE_FACTOR,
    MODEL_DIR,
    RANDOM_STATE,
    REGRESSION_CATEGORICAL_FEATURES,
    REGRESSION_NUMERIC_FEATURES,
    TARGET,
)

try:
    from xgboost import XGBClassifier, XGBRegressor
except ImportError:  # pragma: no cover - optional dependency
    XGBClassifier = None
    XGBRegressor = None


def make_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", make_encoder()),
                    ]
                ),
                categorical_features,
            ),
        ]
    )


def build_pipeline(model, numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    return Pipeline(
        [
            ("preprocessor", build_preprocessor(numeric_features, categorical_features)),
            ("model", model),
        ]
    )


def build_tree_preprocessor(features: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "tree_features",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent"))]),
                features,
            )
        ],
        remainder="drop",
    )


def build_tree_pipeline(model, features: list[str]) -> Pipeline:
    return Pipeline(
        [
            ("preprocessor", build_tree_preprocessor(features)),
            ("model", model),
        ]
    )


def build_model_pipeline(model, numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    if XGBRegressor is not None and isinstance(model, XGBRegressor):
        return build_tree_pipeline(model, numeric_features + categorical_features)
    if XGBClassifier is not None and isinstance(model, XGBClassifier):
        return build_tree_pipeline(model, numeric_features + categorical_features)
    return build_pipeline(model, numeric_features, categorical_features)


def metric_block(y_true: pd.Series, y_pred: np.ndarray, prefix: str) -> dict[str, float]:
    mse = mean_squared_error(y_true, y_pred)
    return {
        f"{prefix}_mae": mean_absolute_error(y_true, y_pred),
        f"{prefix}_rmse": mse**0.5,
        f"{prefix}_r2": r2_score(y_true, y_pred),
    }


def cross_validation_block(pipeline: Pipeline, x_data: pd.DataFrame, y_data: pd.Series) -> dict[str, float]:
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_validate(
        clone(pipeline),
        x_data,
        y_data,
        cv=cv,
        scoring={
            "mae": "neg_mean_absolute_error",
            "rmse": "neg_root_mean_squared_error",
            "r2": "r2",
        },
        n_jobs=-1,
    )
    return {
        "cv_mae": -scores["test_mae"].mean(),
        "cv_rmse": -scores["test_rmse"].mean(),
        "cv_r2": scores["test_r2"].mean(),
    }


def regression_candidates() -> dict[str, object]:
    candidates = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=400, random_state=RANDOM_STATE, n_jobs=-1),
        "svr_rbf": SVR(kernel="rbf", C=10.0, epsilon=0.1),
    }
    if XGBRegressor is not None:
        candidates["xgboost"] = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=400,
            learning_rate=0.08,
            max_depth=2,
            min_child_weight=5,
            subsample=0.9,
            colsample_bytree=0.7,
            gamma=0.0,
            reg_alpha=0.0,
            reg_lambda=1.5,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            tree_method="hist",
        )
    return candidates


def classifier_candidates() -> dict[str, object]:
    candidates = {
        "logistic_regression": LogisticRegression(max_iter=5000, class_weight="balanced"),
        "random_forest_classifier": RandomForestClassifier(
            n_estimators=500,
            max_depth=6,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "hist_gradient_boosting_classifier": HistGradientBoostingClassifier(
            learning_rate=0.04,
            max_iter=350,
            max_leaf_nodes=15,
            l2_regularization=0.5,
            random_state=RANDOM_STATE,
        ),
    }
    if XGBClassifier is not None:
        candidates["xgboost_classifier"] = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            n_estimators=1000,
            learning_rate=0.02,
            max_depth=2,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=1,
            gamma=0.05,
            reg_alpha=0.0,
            reg_lambda=2.0,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            tree_method="hist",
        )
    return candidates


def train_regression_models(df: pd.DataFrame) -> tuple[Pipeline, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    x_data = df.drop(columns=[TARGET, "StudentID", "GradeClass"]).copy()
    y_data = df[TARGET].copy()
    x_train, x_test, y_train, y_test = train_test_split(
        x_data,
        y_data,
        test_size=0.2,
        random_state=RANDOM_STATE,
    )

    records = []
    fitted = {}
    for model_name, model in regression_candidates().items():
        pipeline = build_model_pipeline(model, REGRESSION_NUMERIC_FEATURES, REGRESSION_CATEGORICAL_FEATURES)
        pipeline.fit(x_train, y_train)
        train_predictions = pipeline.predict(x_train)
        test_predictions = pipeline.predict(x_test)

        record = {"model": model_name}
        record.update(metric_block(y_train, train_predictions, "train"))
        record.update(metric_block(y_test, test_predictions, "test"))
        record.update(cross_validation_block(pipeline, x_data, y_data))
        records.append(record)
        fitted[model_name] = pipeline

    metrics = pd.DataFrame(records).sort_values("test_rmse").reset_index(drop=True)
    best_name = metrics.loc[0, "model"]
    return fitted[best_name], metrics, x_test, y_test, x_data


def train_advice_models(df: pd.DataFrame) -> tuple[CalibratedClassifierCV, Pipeline, pd.DataFrame]:
    x_advice = df[ADVICE_FEATURES].copy()
    y_good = (df[TARGET] >= GOOD_PERFORMANCE_THRESHOLD).astype(int)
    x_train, x_test, y_train, y_test = train_test_split(
        x_advice,
        y_good,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y_good,
    )

    classifier_records = []
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    candidates = classifier_candidates()
    for model_name, model in candidates.items():
        pipeline = build_model_pipeline(model, ADVICE_NUMERIC_FEATURES, ADVICE_CATEGORICAL_FEATURES)
        pipeline.fit(x_train, y_train)
        probabilities = pipeline.predict_proba(x_test)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)
        cv_scores = cross_validate(
            pipeline,
            x_advice,
            y_good,
            cv=cv,
            scoring={
                "roc_auc": "roc_auc",
                "average_precision": "average_precision",
                "f1": "f1",
                "accuracy": "accuracy",
            },
            n_jobs=-1,
        )
        classifier_records.append(
            {
                "model": model_name,
                "test_roc_auc": roc_auc_score(y_test, probabilities),
                "test_avg_precision": average_precision_score(y_test, probabilities),
                "test_accuracy": accuracy_score(y_test, predictions),
                "test_precision": precision_score(y_test, predictions, zero_division=0),
                "test_recall": recall_score(y_test, predictions, zero_division=0),
                "test_f1": f1_score(y_test, predictions, zero_division=0),
                "test_brier": brier_score_loss(y_test, probabilities),
                "cv_roc_auc": cv_scores["test_roc_auc"].mean(),
                "cv_avg_precision": cv_scores["test_average_precision"].mean(),
                "cv_f1": cv_scores["test_f1"].mean(),
                "cv_accuracy": cv_scores["test_accuracy"].mean(),
            }
        )

    metrics = pd.DataFrame(classifier_records).sort_values(
        ["cv_roc_auc", "test_brier"],
        ascending=[False, True],
    ).reset_index(drop=True)
    best_name = metrics.loc[0, "model"]

    classifier = CalibratedClassifierCV(
        estimator=build_model_pipeline(candidates[best_name], ADVICE_NUMERIC_FEATURES, ADVICE_CATEGORICAL_FEATURES),
        method="sigmoid",
        cv=5,
    )
    classifier.fit(x_train, y_train)

    advice_regressor = build_pipeline(LinearRegression(), ADVICE_NUMERIC_FEATURES, ADVICE_CATEGORICAL_FEATURES)
    advice_regressor.fit(x_train, df.loc[x_train.index, TARGET])

    probabilities = classifier.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    calibrated = pd.DataFrame(
        [
            {
                "model": f"{best_name}_calibrated",
                "test_roc_auc": roc_auc_score(y_test, probabilities),
                "test_avg_precision": average_precision_score(y_test, probabilities),
                "test_accuracy": accuracy_score(y_test, predictions),
                "test_precision": precision_score(y_test, predictions, zero_division=0),
                "test_recall": recall_score(y_test, predictions, zero_division=0),
                "test_f1": f1_score(y_test, predictions, zero_division=0),
                "test_brier": brier_score_loss(y_test, probabilities),
            }
        ]
    )
    return classifier, advice_regressor, calibrated


def build_artifacts(data_path: Path = DATA_PATH) -> dict[str, object]:
    df = pd.read_csv(data_path)
    best_regressor, regression_metrics, x_test, y_test, x_data = train_regression_models(df)
    classifier, advice_regressor, classifier_metrics = train_advice_models(df)

    importance = permutation_importance(
        best_regressor,
        x_test,
        y_test,
        n_repeats=20,
        random_state=RANDOM_STATE,
        scoring="neg_root_mean_squared_error",
        n_jobs=-1,
    )
    feature_importance = pd.DataFrame(
        {
            "feature": x_test.columns,
            "importance_mean": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)

    metadata = {
        "dataset_rows": int(df.shape[0]),
        "dataset_columns": int(df.shape[1]),
        "target": TARGET,
        "good_performance_threshold": GOOD_PERFORMANCE_THRESHOLD,
        "good_performance_threshold_10": GOOD_PERFORMANCE_THRESHOLD_10,
        "mexican_scale_factor": MEXICAN_SCALE_FACTOR,
        "advice_features": ADVICE_FEATURES,
        "actionable_features": ACTIONABLE_FEATURES,
        "excluded_from_advice": EXCLUDED_FROM_ADVICE,
        "best_regression_model": regression_metrics.loc[0, "model"],
        "regression_metrics": regression_metrics.to_dict(orient="records"),
        "classifier_metrics": classifier_metrics.to_dict(orient="records"),
        "top_features": feature_importance.head(8).to_dict(orient="records"),
    }
    return {
        "gpa_regressor": best_regressor,
        "good_performance_classifier": classifier,
        "advice_regressor": advice_regressor,
        "metadata": metadata,
    }


def save_artifacts(
    artifact_path: Path = ARTIFACT_PATH,
    metadata_path: Path = METADATA_PATH,
    data_path: Path = DATA_PATH,
) -> dict[str, object]:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifacts = build_artifacts(data_path=data_path)
    joblib.dump(artifacts, artifact_path)
    metadata_path.write_text(json.dumps(artifacts["metadata"], indent=2), encoding="utf-8")
    return artifacts["metadata"]
