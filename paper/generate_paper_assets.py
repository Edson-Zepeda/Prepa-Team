"""Generate reproducible tables and figures for the GPA paper."""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR

try:
    from xgboost import XGBClassifier, XGBRegressor
except ImportError:  # pragma: no cover - optional dependency
    XGBClassifier = None
    XGBRegressor = None


RANDOM_STATE = 42
DATA_PATH = Path("data/raw/student_performance.csv")
PAPER_DIR = Path("paper")
FIG_DIR = PAPER_DIR / "figures"
TABLE_DIR = PAPER_DIR / "tables"

TARGET = "GPA"
GOOD_PERFORMANCE_THRESHOLD = 2.5
DROP_COLUMNS = ["StudentID", "GradeClass"]
NUMERIC_FEATURES = ["Age", "StudyTimeWeekly", "Absences"]
CATEGORICAL_FEATURES = [
    "Gender",
    "Ethnicity",
    "ParentalEducation",
    "Tutoring",
    "ParentalSupport",
    "Extracurricular",
    "Sports",
    "Music",
    "Volunteering",
]

ADVICE_NUMERIC_FEATURES = ["Age", "StudyTimeWeekly", "Absences"]
ADVICE_CATEGORICAL_FEATURES = [
    "ParentalEducation",
    "Tutoring",
    "ParentalSupport",
    "Extracurricular",
    "Sports",
    "Music",
    "Volunteering",
]
ADVICE_FEATURES = ADVICE_NUMERIC_FEATURES + ADVICE_CATEGORICAL_FEATURES
EXCLUDED_FROM_ADVICE = ["StudentID", "GradeClass", "Gender", "Ethnicity"]


def make_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # scikit-learn < 1.2
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


def build_pipeline(model, numeric_features: list[str] | None = None, categorical_features: list[str] | None = None):
    numeric_features = numeric_features or NUMERIC_FEATURES
    categorical_features = categorical_features or CATEGORICAL_FEATURES
    return Pipeline(
        [
            ("preprocessor", build_preprocessor(numeric_features, categorical_features)),
            ("model", model),
        ]
    )


def metric_block(y_true, y_pred, prefix: str) -> dict[str, float]:
    mse = mean_squared_error(y_true, y_pred)
    return {
        f"{prefix}_mae": mean_absolute_error(y_true, y_pred),
        f"{prefix}_rmse": mse**0.5,
        f"{prefix}_r2": r2_score(y_true, y_pred),
    }


def cross_validation_block(pipeline, X, y) -> dict[str, float]:
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_validate(
        clone(pipeline),
        X,
        y,
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


def save_table(df: pd.DataFrame, name: str) -> None:
    df.to_csv(TABLE_DIR / name, index=False)


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIG_DIR / name, dpi=240, bbox_inches="tight")
    plt.close()


def build_classifier_candidates() -> dict[str, object]:
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
            n_estimators=500,
            learning_rate=0.03,
            max_depth=2,
            subsample=0.9,
            colsample_bytree=0.8,
            min_child_weight=3,
            reg_lambda=2.0,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            tree_method="hist",
        )
    return candidates


def build_action_options(case: pd.Series):
    absence_options = [("mantener ausencias", 0, lambda x: None)]
    for reduction in [5, 10, 15]:
        if case["Absences"] >= reduction:
            absence_options.append(
                (
                    f"reducir ausencias en {reduction}",
                    reduction,
                    lambda x, r=reduction: x.__setitem__("Absences", max(0, int(x["Absences"]) - r)),
                )
            )
    if case["Absences"] > 5:
        target_absences = 5
        reduction = int(case["Absences"]) - target_absences
        absence_options.append(
            (
                "reducir ausencias a maximo 5",
                max(reduction, 1),
                lambda x, target=target_absences: x.__setitem__("Absences", min(int(x["Absences"]), target)),
            )
        )

    study_options = [("mantener horas de estudio", 0, lambda x: None)]
    for increase in [3, 5, 8]:
        if case["StudyTimeWeekly"] + increase <= 20:
            study_options.append(
                (
                    f"aumentar estudio en {increase}h/semana",
                    increase,
                    lambda x, h=increase: x.__setitem__(
                        "StudyTimeWeekly", min(20, float(x["StudyTimeWeekly"]) + h)
                    ),
                )
            )
    if case["StudyTimeWeekly"] < 20:
        increase = 20 - float(case["StudyTimeWeekly"])
        study_options.append(
            (
                "aumentar estudio hasta 20h/semana",
                int(round(increase)),
                lambda x: x.__setitem__("StudyTimeWeekly", 20.0),
            )
        )

    tutoring_options = [("mantener tutoring", 0, lambda x: None)]
    if int(case["Tutoring"]) == 0:
        tutoring_options.append(("activar tutoring", 2, lambda x: x.__setitem__("Tutoring", 1)))

    support_options = [("mantener apoyo parental", 0, lambda x: None)]
    for increase in [1, 2]:
        if int(case["ParentalSupport"]) + increase <= 4:
            support_options.append(
                (
                    f"aumentar apoyo parental en {increase}",
                    increase,
                    lambda x, h=increase: x.__setitem__(
                        "ParentalSupport", min(4, int(x["ParentalSupport"]) + h)
                    ),
                )
            )

    activity_options = [("mantener actividades", 0, lambda x: None)]
    for activity in ["Extracurricular", "Sports", "Music", "Volunteering"]:
        if int(case[activity]) == 0:
            activity_options.append((f"activar {activity}", 1, lambda x, a=activity: x.__setitem__(a, 1)))

    return absence_options, study_options, tutoring_options, support_options, activity_options


def plan_name(parts: list[str]) -> str:
    chosen = [part for part in parts if not part.startswith("mantener")]
    return " + ".join(chosen) if chosen else "sin cambios"


def group_audit(y_true, y_pred, probabilities, groups: pd.Series, group_name: str) -> list[dict[str, float | int | str]]:
    rows = []
    for value in sorted(groups.dropna().unique()):
        mask = groups == value
        if mask.sum() == 0:
            continue
        yt = y_true[mask]
        yp = y_pred[mask]
        pp = probabilities[mask]
        tn, fp, fn, tp = confusion_matrix(yt, yp, labels=[0, 1]).ravel()
        rows.append(
            {
                "variable": group_name,
                "grupo": int(value) if float(value).is_integer() else value,
                "n": int(mask.sum()),
                "positive_rate_real": float(yt.mean()),
                "positive_rate_pred": float(yp.mean()),
                "mean_probability": float(pp.mean()),
                "accuracy": accuracy_score(yt, yp),
                "precision": precision_score(yt, yp, zero_division=0),
                "recall": recall_score(yt, yp, zero_division=0),
                "f1": f1_score(yt, yp, zero_division=0),
                "false_positive_rate": fp / (fp + tn) if (fp + tn) else 0.0,
                "false_negative_rate": fn / (fn + tp) if (fn + tp) else 0.0,
            }
        )
    return rows


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=[TARGET, *DROP_COLUMNS]).copy()
    y = df[TARGET].copy()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)

    raw_summary = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": df.dtypes.astype(str).values,
            "unique_values": [df[col].nunique() for col in df.columns],
            "min": [df[col].min() for col in df.columns],
            "max": [df[col].max() for col in df.columns],
            "missing": [df[col].isna().sum() for col in df.columns],
        }
    )
    save_table(raw_summary, "table_dataset_summary.csv")

    plt.figure(figsize=(7.2, 4.2))
    plt.hist(df[TARGET], bins=24, color="#4C78A8", edgecolor="white")
    plt.axvline(GOOD_PERFORMANCE_THRESHOLD, color="#E45756", linestyle="--", linewidth=2, label="Umbral GPA >= 2.5")
    plt.xlabel("GPA")
    plt.ylabel("Numero de estudiantes")
    plt.title("Distribucion del GPA en el dataset")
    plt.legend()
    savefig("fig_gpa_distribution.png")

    y_good_all = (df[TARGET] >= GOOD_PERFORMANCE_THRESHOLD).astype(int)
    balance_counts = y_good_all.value_counts().sort_index()
    plt.figure(figsize=(5.6, 4.0))
    plt.bar(["GPA < 2.5", "GPA >= 2.5"], balance_counts.values, color=["#E45756", "#54A24B"])
    plt.ylabel("Numero de estudiantes")
    plt.title("Balance del objetivo de buen rendimiento")
    for idx, value in enumerate(balance_counts.values):
        plt.text(idx, value + 20, str(value), ha="center", fontsize=10)
    savefig("fig_good_performance_balance.png")

    models = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=400, random_state=RANDOM_STATE, n_jobs=-1),
        "svr_rbf": SVR(kernel="rbf", C=10.0, epsilon=0.1),
    }
    if XGBRegressor is not None:
        models["xgboost"] = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=400,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )

    metrics_records = []
    fitted_pipelines = {}
    for model_name, model in models.items():
        pipeline = build_pipeline(model)
        pipeline.fit(X_train, y_train)
        train_predictions = pipeline.predict(X_train)
        test_predictions = pipeline.predict(X_test)
        record = {"model": model_name}
        record.update(metric_block(y_train, train_predictions, "train"))
        record.update(metric_block(y_test, test_predictions, "test"))
        record.update(cross_validation_block(pipeline, X, y))
        metrics_records.append(record)
        fitted_pipelines[model_name] = pipeline

    metrics_df = pd.DataFrame(metrics_records).sort_values("test_rmse").reset_index(drop=True)
    save_table(metrics_df, "table_regression_metrics.csv")

    best_model_name = metrics_df.loc[0, "model"]
    best_row = metrics_df.iloc[0]
    best_pipeline = fitted_pipelines[best_model_name]
    best_predictions = pd.Series(best_pipeline.predict(X_test), index=y_test.index)
    predictions_df = pd.DataFrame(
        {
            "actual_gpa": y_test,
            "predicted_gpa": best_predictions,
        }
    )
    predictions_df["residual"] = predictions_df["actual_gpa"] - predictions_df["predicted_gpa"]
    predictions_df["abs_error"] = predictions_df["residual"].abs()
    save_table(predictions_df.reset_index(names="row_id"), "table_test_predictions.csv")

    plot_metrics = metrics_df.sort_values("test_rmse")
    positions = np.arange(len(plot_metrics))
    width = 0.36
    plt.figure(figsize=(8.5, 4.6))
    plt.bar(positions - width / 2, plot_metrics["test_rmse"], width, label="Test RMSE", color="#4C78A8")
    plt.bar(positions + width / 2, plot_metrics["cv_rmse"], width, label="CV RMSE", color="#F58518")
    plt.xticks(positions, plot_metrics["model"], rotation=15, ha="right")
    plt.ylabel("RMSE")
    plt.title("Comparacion de modelos de regresion")
    plt.legend()
    savefig("fig_model_comparison.png")

    plt.figure(figsize=(5.6, 5.2))
    plt.scatter(y_test, best_predictions, alpha=0.65, color="#E45756", edgecolor="white", linewidth=0.4)
    plt.plot([0, 4], [0, 4], linestyle="--", color="black", linewidth=1)
    plt.xlabel("GPA real")
    plt.ylabel("GPA predicho")
    plt.title(f"Real vs predicho ({best_model_name})")
    savefig("fig_actual_vs_predicted.png")

    plt.figure(figsize=(6.4, 4.0))
    plt.hist(predictions_df["residual"], bins=26, color="#72B7B2", edgecolor="white")
    plt.axvline(0, color="black", linestyle="--", linewidth=1)
    plt.xlabel("Residual")
    plt.ylabel("Frecuencia")
    plt.title("Distribucion de residuales")
    savefig("fig_residual_distribution.png")

    importance = permutation_importance(
        best_pipeline,
        X_test,
        y_test,
        n_repeats=20,
        random_state=RANDOM_STATE,
        scoring="neg_root_mean_squared_error",
        n_jobs=-1,
    )
    importance_df = (
        pd.DataFrame(
            {
                "feature": X_test.columns,
                "importance_mean": importance.importances_mean,
                "importance_std": importance.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )
    save_table(importance_df, "table_feature_importance.csv")

    top_features = importance_df.head(8).sort_values("importance_mean")
    plt.figure(figsize=(7.6, 4.6))
    plt.barh(top_features["feature"], top_features["importance_mean"], xerr=top_features["importance_std"], color="#54A24B")
    plt.xlabel("Aumento medio de RMSE al permutar")
    plt.title("Importancia de variables por permutacion")
    savefig("fig_feature_importance.png")

    xgb_similarity = None
    if "xgboost" in fitted_pipelines:
        lr_pred = pd.Series(fitted_pipelines["linear_regression"].predict(X_test), index=y_test.index)
        xgb_pred = pd.Series(fitted_pipelines["xgboost"].predict(X_test), index=y_test.index)
        xgb_analysis_df = metrics_df[metrics_df["model"].isin(["linear_regression", "xgboost"])][
            ["model", "train_rmse", "test_rmse", "cv_rmse", "train_r2", "test_r2", "cv_r2"]
        ].copy()
        xgb_analysis_df["gap_rmse"] = xgb_analysis_df["test_rmse"] - xgb_analysis_df["train_rmse"]
        xgb_analysis_df["gap_r2"] = xgb_analysis_df["train_r2"] - xgb_analysis_df["test_r2"]
        xgb_similarity = {
            "mean_abs_diff_lr_vs_xgb": float((lr_pred - xgb_pred).abs().mean()),
            "max_abs_diff_lr_vs_xgb": float((lr_pred - xgb_pred).abs().max()),
            "prediction_correlation": float(lr_pred.corr(xgb_pred)),
            "share_lr_better": float(((y_test - lr_pred).abs() < (y_test - xgb_pred).abs()).mean()),
            "share_xgb_better": float(((y_test - xgb_pred).abs() < (y_test - lr_pred).abs()).mean()),
        }
        save_table(xgb_analysis_df, "table_xgboost_analysis.csv")
        save_table(pd.DataFrame([xgb_similarity]), "table_xgboost_similarity.csv")
        plt.figure(figsize=(5.8, 5.2))
        plt.scatter(lr_pred, xgb_pred, alpha=0.65, color="#4C78A8", edgecolor="white", linewidth=0.4)
        min_pred = min(lr_pred.min(), xgb_pred.min())
        max_pred = max(lr_pred.max(), xgb_pred.max())
        plt.plot([min_pred, max_pred], [min_pred, max_pred], linestyle="--", color="black", linewidth=1)
        plt.xlabel("Prediccion LinearRegression")
        plt.ylabel("Prediccion XGBoost")
        plt.title("Similitud entre predicciones LR y XGBoost")
        savefig("fig_xgb_lr_predictions.png")

    X_wo_absences = X.drop(columns=["Absences"])
    X_train_wo, X_test_wo, y_train_wo, y_test_wo = train_test_split(
        X_wo_absences, y, test_size=0.2, random_state=RANDOM_STATE
    )
    numeric_wo_absences = ["Age", "StudyTimeWeekly"]
    no_absences_records = []
    for model_name, model in models.items():
        base_row = metrics_df.loc[metrics_df["model"] == model_name].iloc[0]
        pipeline_wo = build_pipeline(clone(model), numeric_features=numeric_wo_absences, categorical_features=CATEGORICAL_FEATURES)
        pipeline_wo.fit(X_train_wo, y_train_wo)
        pred_wo = pipeline_wo.predict(X_test_wo)
        rmse_wo = mean_squared_error(y_test_wo, pred_wo) ** 0.5
        r2_wo = r2_score(y_test_wo, pred_wo)
        no_absences_records.append(
            {
                "model": model_name,
                "rmse_base": base_row["test_rmse"],
                "rmse_without_absences": rmse_wo,
                "delta_rmse": rmse_wo - base_row["test_rmse"],
                "r2_base": base_row["test_r2"],
                "r2_without_absences": r2_wo,
                "delta_r2": r2_wo - base_row["test_r2"],
            }
        )
    no_absences_df = pd.DataFrame(no_absences_records).sort_values("rmse_without_absences").reset_index(drop=True)
    save_table(no_absences_df, "table_ablation_absences.csv")

    plot_ablation = no_absences_df.set_index("model")[["rmse_base", "rmse_without_absences"]]
    ax = plot_ablation.plot(kind="bar", figsize=(8.4, 4.6), color=["#4C78A8", "#E45756"])
    ax.set_ylabel("RMSE")
    ax.set_title("Impacto de remover Absences")
    ax.tick_params(axis="x", rotation=15)
    ax.legend(["Base", "Sin Absences"])
    savefig("fig_ablation_absences.png")

    X_advice = df[ADVICE_FEATURES].copy()
    y_good = (df[TARGET] >= GOOD_PERFORMANCE_THRESHOLD).astype(int)
    X_train_adv, X_test_adv, y_train_good, y_test_good = train_test_split(
        X_advice, y_good, test_size=0.2, random_state=RANDOM_STATE, stratify=y_good
    )

    classifier_candidates = build_classifier_candidates()
    cv_classifier = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    classifier_records = []
    for model_name, model in classifier_candidates.items():
        pipeline = build_pipeline(model, numeric_features=ADVICE_NUMERIC_FEATURES, categorical_features=ADVICE_CATEGORICAL_FEATURES)
        pipeline.fit(X_train_adv, y_train_good)
        probabilities = pipeline.predict_proba(X_test_adv)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)
        cv_scores = cross_validate(
            pipeline,
            X_advice,
            y_good,
            cv=cv_classifier,
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
                "test_roc_auc": roc_auc_score(y_test_good, probabilities),
                "test_avg_precision": average_precision_score(y_test_good, probabilities),
                "test_accuracy": accuracy_score(y_test_good, predictions),
                "test_precision": precision_score(y_test_good, predictions, zero_division=0),
                "test_recall": recall_score(y_test_good, predictions, zero_division=0),
                "test_f1": f1_score(y_test_good, predictions, zero_division=0),
                "test_brier": brier_score_loss(y_test_good, probabilities),
                "cv_roc_auc": cv_scores["test_roc_auc"].mean(),
                "cv_avg_precision": cv_scores["test_average_precision"].mean(),
                "cv_f1": cv_scores["test_f1"].mean(),
                "cv_accuracy": cv_scores["test_accuracy"].mean(),
            }
        )

    classifier_metrics_df = pd.DataFrame(classifier_records).sort_values(
        ["cv_roc_auc", "test_brier"], ascending=[False, True]
    ).reset_index(drop=True)
    save_table(classifier_metrics_df, "table_classifier_candidates.csv")

    best_classifier_name = classifier_metrics_df.loc[0, "model"]
    best_base_classifier = classifier_candidates[best_classifier_name]
    best_classifier_pipeline = CalibratedClassifierCV(
        estimator=build_pipeline(
            best_base_classifier,
            numeric_features=ADVICE_NUMERIC_FEATURES,
            categorical_features=ADVICE_CATEGORICAL_FEATURES,
        ),
        method="sigmoid",
        cv=5,
    )
    best_classifier_pipeline.fit(X_train_adv, y_train_good)
    calibrated_probabilities = best_classifier_pipeline.predict_proba(X_test_adv)[:, 1]
    calibrated_predictions = (calibrated_probabilities >= 0.5).astype(int)
    calibrated_metrics_df = pd.DataFrame(
        [
            {
                "model": f"{best_classifier_name}_calibrated",
                "test_roc_auc": roc_auc_score(y_test_good, calibrated_probabilities),
                "test_avg_precision": average_precision_score(y_test_good, calibrated_probabilities),
                "test_accuracy": accuracy_score(y_test_good, calibrated_predictions),
                "test_precision": precision_score(y_test_good, calibrated_predictions, zero_division=0),
                "test_recall": recall_score(y_test_good, calibrated_predictions, zero_division=0),
                "test_f1": f1_score(y_test_good, calibrated_predictions, zero_division=0),
                "test_brier": brier_score_loss(y_test_good, calibrated_probabilities),
            }
        ]
    )
    save_table(calibrated_metrics_df, "table_classifier_calibrated.csv")

    cm = confusion_matrix(y_test_good, calibrated_predictions, labels=[0, 1])
    plt.figure(figsize=(4.8, 4.2))
    plt.imshow(cm, cmap="Blues")
    plt.title("Matriz de confusion del clasificador")
    plt.xticks([0, 1], ["Pred. <2.5", "Pred. >=2.5"])
    plt.yticks([0, 1], ["Real <2.5", "Real >=2.5"])
    for (i, j), value in np.ndenumerate(cm):
        plt.text(j, i, int(value), ha="center", va="center", color="black", fontsize=12)
    plt.colorbar(fraction=0.046, pad=0.04)
    savefig("fig_confusion_matrix.png")

    fpr, tpr, _ = roc_curve(y_test_good, calibrated_probabilities)
    precision, recall, _ = precision_recall_curve(y_test_good, calibrated_probabilities)
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
    axes[0].plot(fpr, tpr, color="#4C78A8", linewidth=2)
    axes[0].plot([0, 1], [0, 1], color="black", linestyle="--", linewidth=1)
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].set_title(f"ROC AUC = {roc_auc_score(y_test_good, calibrated_probabilities):.4f}")
    axes[1].plot(recall, precision, color="#F58518", linewidth=2)
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title(f"Average Precision = {average_precision_score(y_test_good, calibrated_probabilities):.4f}")
    savefig("fig_roc_pr_curves.png")

    prob_true, prob_pred = calibration_curve(y_test_good, calibrated_probabilities, n_bins=8, strategy="uniform")
    plt.figure(figsize=(5.4, 4.6))
    plt.plot(prob_pred, prob_true, marker="o", color="#54A24B", linewidth=2)
    plt.plot([0, 1], [0, 1], color="black", linestyle="--", linewidth=1)
    plt.xlabel("Probabilidad predicha")
    plt.ylabel("Frecuencia observada")
    plt.title("Curva de calibracion")
    savefig("fig_calibration_curve.png")

    sensitive_test = df.loc[X_test_adv.index, ["Gender", "Ethnicity"]].copy()
    fairness_rows = []
    for sensitive_col in ["Gender", "Ethnicity"]:
        fairness_rows.extend(
            group_audit(
                y_test_good.to_numpy(),
                calibrated_predictions,
                calibrated_probabilities,
                sensitive_test[sensitive_col].reset_index(drop=True),
                sensitive_col,
            )
        )
    fairness_df = pd.DataFrame(fairness_rows)
    save_table(fairness_df, "table_fairness_audit.csv")

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
    for ax, sensitive_col in zip(axes, ["Gender", "Ethnicity"]):
        subset = fairness_df[fairness_df["variable"] == sensitive_col]
        xlabels = [f"{sensitive_col}={g}" for g in subset["grupo"]]
        x = np.arange(len(subset))
        ax.bar(x - 0.18, subset["false_negative_rate"], width=0.36, label="FNR", color="#E45756")
        ax.bar(x + 0.18, subset["false_positive_rate"], width=0.36, label="FPR", color="#4C78A8")
        ax.set_xticks(x)
        ax.set_xticklabels(xlabels, rotation=25, ha="right")
        ax.set_ylim(0, max(0.35, subset[["false_negative_rate", "false_positive_rate"]].to_numpy().max() + 0.05))
        ax.set_title(f"Auditoria por {sensitive_col}")
        ax.legend()
    savefig("fig_fairness_audit.png")

    advice_regressor = build_pipeline(
        LinearRegression(), numeric_features=ADVICE_NUMERIC_FEATURES, categorical_features=ADVICE_CATEGORICAL_FEATURES
    )
    advice_regressor.fit(X_train_adv, y.loc[X_train_adv.index])

    case_pool = X_test_adv.copy()
    case_pool["predicted_probability"] = calibrated_probabilities
    case_pool["predicted_gpa"] = advice_regressor.predict(X_test_adv)
    current_case = case_pool.sort_values(
        ["predicted_probability", "predicted_gpa", "Absences", "StudyTimeWeekly"], ascending=[True, True, False, True]
    ).iloc[0][ADVICE_FEATURES].copy()

    current_gpa = float(np.clip(advice_regressor.predict(pd.DataFrame([current_case]))[0], 0, 4))
    current_prob = float(best_classifier_pipeline.predict_proba(pd.DataFrame([current_case]))[0, 1])

    plan_records = []
    action_options = build_action_options(current_case)
    for option_combo in product(*action_options):
        actions, efforts, mutators = zip(*option_combo)
        name = plan_name(list(actions))
        if name == "sin cambios":
            continue
        scenario = current_case.copy()
        for mutator in mutators:
            mutator(scenario)
        scenario_gpa = float(np.clip(advice_regressor.predict(pd.DataFrame([scenario]))[0], 0, 4))
        scenario_prob = float(best_classifier_pipeline.predict_proba(pd.DataFrame([scenario]))[0, 1])
        plan_records.append(
            {
                "plan": name,
                "gpa_actual": current_gpa,
                "gpa_estimado": scenario_gpa,
                "delta_gpa": scenario_gpa - current_gpa,
                "prob_actual": current_prob,
                "prob_estimada": scenario_prob,
                "delta_prob": scenario_prob - current_prob,
                "esfuerzo": sum(efforts),
                "Absences_plan": scenario["Absences"],
                "StudyTimeWeekly_plan": scenario["StudyTimeWeekly"],
                "Tutoring_plan": scenario["Tutoring"],
                "ParentalSupport_plan": scenario["ParentalSupport"],
            }
        )
    recommendation_plans_df = (
        pd.DataFrame(plan_records)
        .sort_values(["delta_prob", "delta_gpa", "esfuerzo"], ascending=[False, False, True])
        .head(10)
        .reset_index(drop=True)
    )
    save_table(recommendation_plans_df, "table_recommendation_plans.csv")

    best_plan = recommendation_plans_df.iloc[0]
    rec_plot = pd.DataFrame(
        {
            "escenario": ["Actual", "Plan recomendado"],
            "GPA": [best_plan["gpa_actual"], best_plan["gpa_estimado"]],
            "Probabilidad": [best_plan["prob_actual"], best_plan["prob_estimada"]],
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.0))
    axes[0].bar(rec_plot["escenario"], rec_plot["GPA"], color=["#E45756", "#54A24B"])
    axes[0].set_ylim(0, 4)
    axes[0].set_title("Cambio estimado de GPA")
    axes[0].set_ylabel("GPA")
    axes[1].bar(rec_plot["escenario"], rec_plot["Probabilidad"] * 100, color=["#E45756", "#54A24B"])
    axes[1].set_ylim(0, 100)
    axes[1].set_title("Probabilidad de GPA >= 2.5")
    axes[1].set_ylabel("Porcentaje")
    for ax in axes:
        ax.tick_params(axis="x", rotation=10)
    savefig("fig_recommendation_plan.png")

    summary = {
        "dataset": {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "missing_total": int(df.isna().sum().sum()),
            "gpa_min": float(df[TARGET].min()),
            "gpa_max": float(df[TARGET].max()),
            "gpa_mean": float(df[TARGET].mean()),
            "good_performance_threshold": GOOD_PERFORMANCE_THRESHOLD,
            "good_performance_count": int(y_good_all.sum()),
            "low_performance_count": int((1 - y_good_all).sum()),
            "absences_gpa_corr": float(df["Absences"].corr(df[TARGET])),
        },
        "best_regression_model": best_model_name,
        "best_regression_metrics": {key: float(best_row[key]) for key in metrics_df.columns if key != "model"},
        "top_features": importance_df.head(5).to_dict(orient="records"),
        "xgboost_similarity": xgb_similarity,
        "best_classifier": f"{best_classifier_name}_calibrated",
        "classifier_metrics": calibrated_metrics_df.iloc[0].to_dict(),
        "best_recommendation_plan": best_plan.to_dict(),
        "excluded_from_advice": EXCLUDED_FROM_ADVICE,
    }
    (PAPER_DIR / "paper_metrics_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
