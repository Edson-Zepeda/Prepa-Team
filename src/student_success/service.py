from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import (
    ADVICE_FEATURES,
    ARTIFACT_PATH,
    EXCLUDED_FROM_ADVICE,
    FIELD_LIMITS,
    GOOD_PERFORMANCE_THRESHOLD,
    GOOD_PERFORMANCE_THRESHOLD_10,
    MEXICAN_SCALE_FACTOR,
)
from .training import save_artifacts


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


def _clip_gpa(value: float) -> float:
    return float(np.clip(value, 0, 4))


def _gpa_to_average_10(value: float) -> float:
    return float(np.clip(value * MEXICAN_SCALE_FACTOR, 0, 10))


def _risk_level(probability: float) -> str:
    if probability >= 0.75:
        return "bajo"
    if probability >= 0.50:
        return "medio"
    if probability >= 0.25:
        return "alto"
    return "muy alto"


def _display_probability(probability: float) -> str:
    if probability >= 0.995:
        return "99%"
    if probability <= 0.005:
        return "<1%"
    return f"{round(probability * 100):.0f}%"


ACTIVITY_LABELS = {
    "Extracurricular": "actividad extracurricular",
    "Sports": "deportes",
    "Music": "musica",
    "Volunteering": "voluntariado",
}


def _message_for_plan(plan: pd.Series, current_average_10: float, current_probability: float) -> list[str]:
    messages = []
    if plan.get("Absences_plan") is not None:
        messages.append("Reducir ausencias puede subir tu promedio estimado y bajar tu riesgo académico.")
    if plan.get("StudyTimeWeekly_plan") is not None:
        messages.append("Aumentar tus horas de estudio semanal mejora tu probabilidad de buen rendimiento.")
    if plan.get("Tutoring_plan") == 1:
        messages.append("Activar tutoria puede ayudarte a reforzar las materias con mayor dificultad.")
    if plan.get("ParentalSupport_plan") is not None:
        messages.append("Tener mas seguimiento familiar o academico mejora la consistencia de tu desempeno.")
    messages.append(
        f"Tu promedio estimado actual es {current_average_10:.1f}/10 y tu probabilidad actual de mantener un buen rendimiento es {_display_probability(current_probability)}."
    )
    messages.append(
        "Estos resultados son simulaciones del modelo y deben usarse como apoyo academico, no como garantia de calificacion."
    )
    return messages


def _plan_name(parts: list[str]) -> str:
    chosen = [part for part in parts if not part.startswith("mantener")]
    return " + ".join(chosen) if chosen else "sin cambios"


class StudentSuccessService:
    """Prediction and recommendation facade for the school control web app."""

    def __init__(self, artifact_path: Path | str = ARTIFACT_PATH, auto_train: bool = True) -> None:
        self.artifact_path = Path(artifact_path)
        if not self.artifact_path.exists():
            if not auto_train:
                raise FileNotFoundError(f"No model artifact found at {self.artifact_path}")
            save_artifacts(artifact_path=self.artifact_path)

        artifacts = joblib.load(self.artifact_path)
        metadata = artifacts.get("metadata", {})
        if metadata.get("good_performance_threshold_10") != GOOD_PERFORMANCE_THRESHOLD_10 and auto_train:
            save_artifacts(artifact_path=self.artifact_path)
            artifacts = joblib.load(self.artifact_path)

        self.gpa_regressor = artifacts["gpa_regressor"]
        self.good_performance_classifier = artifacts["good_performance_classifier"]
        self.advice_regressor = artifacts["advice_regressor"]
        self.metadata = artifacts["metadata"]

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "required_fields": ADVICE_FEATURES,
            "field_limits": FIELD_LIMITS,
            "excluded_from_advice": EXCLUDED_FROM_ADVICE,
            "good_performance_threshold": GOOD_PERFORMANCE_THRESHOLD,
            "good_performance_threshold_10": GOOD_PERFORMANCE_THRESHOLD_10,
            "mexican_scale_factor": MEXICAN_SCALE_FACTOR,
        }

    def validate_payload(self, payload: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for field in ADVICE_FEATURES:
            if field not in payload:
                issues.append(ValidationIssue(field, "Campo requerido."))
                continue
            try:
                value = float(payload[field])
            except (TypeError, ValueError):
                issues.append(ValidationIssue(field, "Debe ser numérico."))
                continue

            lower, upper = FIELD_LIMITS[field]
            if value < lower or value > upper:
                issues.append(ValidationIssue(field, f"Debe estar entre {lower} y {upper}."))
        return issues

    def _case_frame(self, payload: dict[str, Any]) -> pd.DataFrame:
        normalized = {}
        for field in ADVICE_FEATURES:
            value = float(payload[field])
            if field not in {"StudyTimeWeekly"}:
                value = int(value)
            normalized[field] = value
        return pd.DataFrame([normalized], columns=ADVICE_FEATURES)

    def _predict_gpa(self, case: pd.DataFrame) -> float:
        return _clip_gpa(float(self.advice_regressor.predict(case)[0]))

    def _predict_gpa_batch(self, cases: pd.DataFrame) -> np.ndarray:
        predictions = self.advice_regressor.predict(cases)
        return np.clip(np.asarray(predictions, dtype=float), 0, 4)

    def _predict_probability(self, case: pd.DataFrame) -> float:
        return float(self.good_performance_classifier.predict_proba(case)[0, 1])

    def _predict_probability_batch(self, cases: pd.DataFrame) -> np.ndarray:
        probabilities = self.good_performance_classifier.predict_proba(cases)[:, 1]
        return np.asarray(probabilities, dtype=float)

    def _intervention_options(self, case: pd.Series):
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
            absence_options.append(
                (
                    "reducir ausencias a maximo 5",
                    int(case["Absences"]) - 5,
                    lambda x: x.__setitem__("Absences", min(int(x["Absences"]), 5)),
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
            study_options.append(
                (
                    "aumentar estudio hasta 20h/semana",
                    int(round(20 - float(case["StudyTimeWeekly"]))),
                    lambda x: x.__setitem__("StudyTimeWeekly", 20.0),
                )
            )

        tutoring_options = [("mantener tutoria", 0, lambda x: None)]
        if int(case["Tutoring"]) == 0:
            tutoring_options.append(("activar tutoria", 2, lambda x: x.__setitem__("Tutoring", 1)))

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
                activity_options.append(
                    (
                        f"activar {ACTIVITY_LABELS[activity]}",
                        1,
                        lambda x, a=activity: x.__setitem__(a, 1),
                    )
                )

        return absence_options, study_options, tutoring_options, support_options, activity_options

    def _recommendation_plans(self, case: pd.Series, current_gpa: float, current_probability: float) -> pd.DataFrame:
        scenarios: list[dict[str, Any]] = []
        for option_combo in product(*self._intervention_options(case)):
            actions, efforts, mutators = zip(*option_combo)
            name = _plan_name(list(actions))
            if name == "sin cambios":
                continue
            scenario = case.copy()
            for mutator in mutators:
                mutator(scenario)
            scenarios.append(
                {
                    "plan": name,
                    "effort": int(sum(efforts)),
                    "Absences_plan": float(scenario["Absences"]),
                    "StudyTimeWeekly_plan": float(scenario["StudyTimeWeekly"]),
                    "Tutoring_plan": int(scenario["Tutoring"]),
                    "ParentalSupport_plan": int(scenario["ParentalSupport"]),
                    **{feature: scenario[feature] for feature in ADVICE_FEATURES},
                }
            )
        if not scenarios:
            return pd.DataFrame()

        scenario_frame = pd.DataFrame(scenarios)
        model_frame = scenario_frame[ADVICE_FEATURES]
        gpa_predictions = self._predict_gpa_batch(model_frame)
        probability_predictions = self._predict_probability_batch(model_frame)

        result = scenario_frame[["plan", "effort", "Absences_plan", "StudyTimeWeekly_plan", "Tutoring_plan", "ParentalSupport_plan"]].copy()
        result["estimated_gpa_after"] = gpa_predictions
        result["probability_after"] = probability_predictions
        result["delta_gpa"] = result["estimated_gpa_after"] - current_gpa
        result["delta_probability"] = result["probability_after"] - current_probability

        return result.sort_values(
            ["delta_probability", "delta_gpa", "effort"],
            ascending=[False, False, True],
        ).reset_index(drop=True)

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        issues = self.validate_payload(payload)
        if issues:
            return {
                "ok": False,
                "errors": [{"field": issue.field, "message": issue.message} for issue in issues],
            }

        case = self._case_frame(payload)
        case_series = case.iloc[0].copy()
        estimated_gpa = self._predict_gpa(case)
        estimated_average_10 = _gpa_to_average_10(estimated_gpa)
        probability = self._predict_probability(case)
        plans = self._recommendation_plans(case_series, estimated_gpa, probability)
        if plans.empty:
            return {
                "ok": True,
                "estimated_average_10": round(estimated_average_10, 2),
                "good_performance_probability": round(probability, 4),
                "good_performance_threshold_10": GOOD_PERFORMANCE_THRESHOLD_10,
                "risk_level": _risk_level(probability),
                "messages": [
                    "El estudiante ya esta en el maximo de las variables accionables simuladas.",
                    "Mantener asistencia, estudio constante y tutoria es la prioridad.",
                    "Estos resultados son simulaciones del modelo y no sustituyen la orientacion de un docente o tutor.",
                ],
                "recommended_plan": {
                    "plan": "mantener habitos actuales",
                    "estimated_average_after_10": round(estimated_average_10, 2),
                    "probability_after": round(probability, 4),
                    "delta_average_10": 0.0,
                    "delta_probability": 0.0,
                    "effort": 0,
                },
                "top_plans": [],
                "excluded_from_advice": EXCLUDED_FROM_ADVICE,
            }

        best_plan = plans.iloc[0]
        best_average_after_10 = _gpa_to_average_10(float(best_plan["estimated_gpa_after"]))

        return {
            "ok": True,
            "estimated_average_10": round(estimated_average_10, 2),
            "good_performance_probability": round(probability, 4),
            "good_performance_threshold_10": GOOD_PERFORMANCE_THRESHOLD_10,
            "risk_level": _risk_level(probability),
            "messages": _message_for_plan(best_plan, estimated_average_10, probability),
            "recommended_plan": {
                "plan": best_plan["plan"],
                "estimated_average_after_10": round(best_average_after_10, 2),
                "probability_after": round(float(best_plan["probability_after"]), 4),
                "delta_average_10": round(best_average_after_10 - estimated_average_10, 2),
                "delta_probability": round(float(best_plan["delta_probability"]), 4),
                "effort": int(best_plan["effort"]),
            },
            "top_plans": [
                {
                    "plan": row["plan"],
                    "estimated_average_after_10": round(_gpa_to_average_10(float(row["estimated_gpa_after"])), 2),
                    "probability_after": round(float(row["probability_after"]), 4),
                    "delta_average_10": round(
                        _gpa_to_average_10(float(row["estimated_gpa_after"])) - estimated_average_10,
                        2,
                    ),
                    "delta_probability": round(float(row["delta_probability"]), 4),
                    "effort": int(row["effort"]),
                }
                for _, row in plans.head(3).iterrows()
            ],
            "excluded_from_advice": EXCLUDED_FROM_ADVICE,
        }
