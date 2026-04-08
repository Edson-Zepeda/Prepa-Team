from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import KFold, RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor

RANDOM_STATE = 42
DATA_PATH = Path("data/raw/student_performance.csv")
DOC_PATH = Path("docs/XGBOOST_AND_NO_ABSENCES_ANALYSIS.md")

TARGET = "GPA"
DROP_COLUMNS = ["StudentID", "GradeClass"]
REGRESSION_NUMERIC = ["Age", "StudyTimeWeekly", "Absences"]
REGRESSION_CATEGORICAL = [
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
ADVICE_NUMERIC = ["Age", "StudyTimeWeekly", "Absences"]
ADVICE_CATEGORICAL = [
    "ParentalEducation",
    "Tutoring",
    "ParentalSupport",
    "Extracurricular",
    "Sports",
    "Music",
    "Volunteering",
]
GOOD_PERFORMANCE_THRESHOLD = 2.5


def make_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_ohe_pipeline(model, numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("encoder", make_encoder())]),
                categorical_features,
            ),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def build_tree_pipeline(model, features: list[str]) -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            (
                "tree_features",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent"))]),
                features,
            )
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def rmse(y_true, y_pred) -> float:
    return mean_squared_error(y_true, y_pred) ** 0.5


def regression_metrics(pipe: Pipeline, x_train, x_test, y_train, y_test) -> dict[str, float]:
    pipe.fit(x_train, y_train)
    train_pred = pipe.predict(x_train)
    test_pred = pipe.predict(x_test)
    return {
        "train_rmse": rmse(y_train, train_pred),
        "test_rmse": rmse(y_test, test_pred),
        "test_r2": r2_score(y_test, test_pred),
    }


def classification_metrics(probabilities, y_true) -> dict[str, float]:
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "roc_auc": roc_auc_score(y_true, probabilities),
        "avg_precision": average_precision_score(y_true, probabilities),
        "accuracy": accuracy_score(y_true, predictions),
        "precision": precision_score(y_true, predictions, zero_division=0),
        "recall": recall_score(y_true, predictions, zero_division=0),
        "f1": f1_score(y_true, predictions, zero_division=0),
        "brier": brier_score_loss(y_true, probabilities),
    }


def format_block(title: str, rows: list[dict[str, object]]) -> str:
    frame = pd.DataFrame(rows)
    headers = frame.columns.tolist()
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in frame.iterrows():
        table.append("| " + " | ".join(str(row[column]) for column in headers) + " |")
    return f"## {title}\n\n" + "\n".join(table) + "\n"


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    x_reg = df.drop(columns=[TARGET, *DROP_COLUMNS]).copy()
    y_reg = df[TARGET].copy()
    x_train_reg, x_test_reg, y_train_reg, y_test_reg = train_test_split(
        x_reg,
        y_reg,
        test_size=0.2,
        random_state=RANDOM_STATE,
    )

    regression_rows = []
    lr_pipe = build_ohe_pipeline(LinearRegression(), REGRESSION_NUMERIC, REGRESSION_CATEGORICAL)
    regression_rows.append({"model": "linear_regression", **regression_metrics(lr_pipe, x_train_reg, x_test_reg, y_train_reg, y_test_reg)})

    xgb_tuned = XGBRegressor(
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
    xgb_pipe = build_tree_pipeline(xgb_tuned, REGRESSION_NUMERIC + REGRESSION_CATEGORICAL)
    regression_rows.append({"model": "xgboost_tuned", **regression_metrics(xgb_pipe, x_train_reg, x_test_reg, y_train_reg, y_test_reg)})

    search_pipe = build_tree_pipeline(
        XGBRegressor(objective="reg:squarederror", random_state=RANDOM_STATE, n_jobs=-1, tree_method="hist"),
        REGRESSION_NUMERIC + REGRESSION_CATEGORICAL,
    )
    search = RandomizedSearchCV(
        search_pipe,
        param_distributions={
            "model__n_estimators": [200, 300, 400, 600, 800, 1000, 1200, 1500],
            "model__learning_rate": [0.01, 0.02, 0.03, 0.05, 0.08],
            "model__max_depth": [2, 3, 4, 5],
            "model__min_child_weight": [1, 2, 3, 5, 7, 10],
            "model__subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
            "model__colsample_bytree": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "model__gamma": [0, 0.01, 0.05, 0.1, 0.2],
            "model__reg_alpha": [0, 0.01, 0.1, 0.3, 0.6, 1.0],
            "model__reg_lambda": [1.0, 1.5, 2.0, 3.0, 5.0, 8.0],
        },
        n_iter=60,
        scoring="neg_root_mean_squared_error",
        cv=KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    search.fit(x_train_reg, y_train_reg)
    search_pred = search.best_estimator_.predict(x_test_reg)
    regression_rows.append(
        {
            "model": "xgboost_random_search",
            "train_rmse": None,
            "test_rmse": rmse(y_test_reg, search_pred),
            "test_r2": r2_score(y_test_reg, search_pred),
            "cv_rmse": -search.best_score_,
        }
    )

    x_reg_wo = df.drop(columns=[TARGET, *DROP_COLUMNS, "Absences"]).copy()
    y_reg_wo = df[TARGET].copy()
    x_train_wo, x_test_wo, y_train_wo, y_test_wo = train_test_split(
        x_reg_wo,
        y_reg_wo,
        test_size=0.2,
        random_state=RANDOM_STATE,
    )
    numeric_wo = ["Age", "StudyTimeWeekly"]
    categorical_wo = [feature for feature in REGRESSION_CATEGORICAL]

    no_absences_rows = []
    no_absences_rows.append(
        {
            "model": "linear_regression_wo_absences",
            **regression_metrics(
                build_ohe_pipeline(LinearRegression(), numeric_wo, categorical_wo),
                x_train_wo,
                x_test_wo,
                y_train_wo,
                y_test_wo,
            ),
        }
    )
    no_absences_rows.append(
        {
            "model": "xgboost_tuned_wo_absences",
            **regression_metrics(
                build_tree_pipeline(
                    XGBRegressor(
                        objective="reg:squarederror",
                        n_estimators=200,
                        learning_rate=0.02,
                        max_depth=2,
                        min_child_weight=5,
                        subsample=0.7,
                        colsample_bytree=0.7,
                        gamma=0.0,
                        reg_alpha=0.0,
                        reg_lambda=2.0,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                        tree_method="hist",
                    ),
                    numeric_wo + categorical_wo,
                ),
                x_train_wo,
                x_test_wo,
                y_train_wo,
                y_test_wo,
            ),
        }
    )

    x_cls = df[ADVICE_NUMERIC + ADVICE_CATEGORICAL].copy()
    y_cls = (df[TARGET] >= GOOD_PERFORMANCE_THRESHOLD).astype(int)
    x_train_cls, x_test_cls, y_train_cls, y_test_cls = train_test_split(
        x_cls,
        y_cls,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y_cls,
    )
    classifier_rows = []

    logistic = build_ohe_pipeline(LogisticRegression(max_iter=5000, class_weight="balanced"), ADVICE_NUMERIC, ADVICE_CATEGORICAL)
    logistic.fit(x_train_cls, y_train_cls)
    classifier_rows.append(
        {
            "model": "logistic_regression",
            **classification_metrics(logistic.predict_proba(x_test_cls)[:, 1], y_test_cls),
        }
    )

    xgb_classifier = build_tree_pipeline(
        XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            n_estimators=1000,
            learning_rate=0.02,
            max_depth=2,
            min_child_weight=1,
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=0.05,
            reg_alpha=0.0,
            reg_lambda=2.0,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            tree_method="hist",
        ),
        ADVICE_NUMERIC + ADVICE_CATEGORICAL,
    )
    xgb_classifier.fit(x_train_cls, y_train_cls)
    classifier_rows.append(
        {
            "model": "xgboost_classifier_tuned",
            **classification_metrics(xgb_classifier.predict_proba(x_test_cls)[:, 1], y_test_cls),
        }
    )

    calibrated_xgb = CalibratedClassifierCV(estimator=xgb_classifier, method="sigmoid", cv=5)
    calibrated_xgb.fit(x_train_cls, y_train_cls)
    classifier_rows.append(
        {
            "model": "xgboost_classifier_tuned_calibrated",
            **classification_metrics(calibrated_xgb.predict_proba(x_test_cls)[:, 1], y_test_cls),
        }
    )

    DOC_PATH.write_text(
        "\n\n".join(
            [
                "# Analisis adicional de XGBoost y escenario sin Absences",
                "Este documento resume el analisis extendido para responder dos preguntas: "
                "1) que pasa al quitar `Absences`, y 2) hasta donde puede mejorar `XGBoost` sin manipular el set de prueba.",
                format_block("Regresion con todas las variables", regression_rows),
                format_block("Regresion sin Absences", no_absences_rows),
                format_block("Clasificacion de buen rendimiento", classifier_rows),
                "## Conclusiones",
                "- En regresion, `XGBoost` mejora con tuning, pero no supera honestamente a `LinearRegression` en este dataset.",
                "- Sin `Absences`, ambos modelos empeoran mucho y `LinearRegression` sigue ligeramente arriba.",
                "- En la tarea de clasificacion para probabilidad de buen rendimiento, `XGBoost` tuneado si supera a `LogisticRegression` en discriminacion y queda como mejor clasificador del proyecto.",
            ]
        ),
        encoding="utf-8",
    )

    print(json.dumps({"regression": regression_rows, "no_absences": no_absences_rows, "classification": classifier_rows}, indent=2))


if __name__ == "__main__":
    main()
