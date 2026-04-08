from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import ADVICE_FEATURES, ARTIFACT_PATH, EXCLUDED_FROM_ADVICE, FIELD_LIMITS, GOOD_PERFORMANCE_THRESHOLD
from .training import save_artifacts


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


def _clip_gpa(value: float) -> float:
    return float(np.clip(value, 0, 4))


def _risk_level(probability: float) -> str:
    if probability >= 0.75:
        return "alta probabilidad de buen rendimiento"
    if probability >= 0.50:
        return "probabilidad media de buen rendimiento"
    if probability >= 0.25:
        return "riesgo moderado"
    return "riesgo alto"


def _message_for_plan(plan: pd.Series) -> list[str]:
    messages = []
    if plan.get("Absences_plan") is not None:
        messages.append("Prioriza reducir ausencias: es el factor con mayor impacto en el modelo.")
    if plan.get("StudyTimeWeekly_plan") is not None:
        messages.append("Aumenta tus horas de estudio semanal de forma sostenida.")
    if plan.get("Tutoring_plan") == 1:
        messages.append("Activa tutoring para reforzar las areas donde tengas mas dificultad.")
    if plan.get("ParentalSupport_plan") is not None:
        messages.append("Busca mayor seguimiento familiar o de un tutor academico.")
    messages.append("Estos resultados son simulaciones del modelo, no una garantia de calificacion.")
    return messages


def _plan_name(parts: list[str]) -> str:
    chosen = [part for part in parts if not part.startswith("mantener")]
    return " + ".join(chosen) if chosen else "sin cambios"


class StudentSuccessService:
    """Prediction and recommendation facade for the web beta."""

    def __init__(self, artifact_path: Path | str = ARTIFACT_PATH, auto_train: bool = True) -> None:
        self.artifact_path = Path(artifact_path)
        if not self.artifact_path.exists():
            if not auto_train:
                raise FileNotFoundError(f"No model artifact found at {self.artifact_path}")
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
                issues.append(ValidationIssue(field, "Debe ser numerico."))
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

    def _predict_probability(self, case: pd.DataFrame) -> float:
        return float(self.good_performance_classifier.predict_proba(case)[0, 1])

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

    def _recommendation_plans(self, case: pd.Series, current_gpa: float, current_probability: float) -> pd.DataFrame:
        records = []
        for option_combo in product(*self._intervention_options(case)):
            actions, efforts, mutators = zip(*option_combo)
            name = _plan_name(list(actions))
            if name == "sin cambios":
                continue
            scenario = case.copy()
            for mutator in mutators:
                mutator(scenario)
            scenario_frame = pd.DataFrame([scenario[ADVICE_FEATURES]], columns=ADVICE_FEATURES)
            estimated_gpa = self._predict_gpa(scenario_frame)
            estimated_probability = self._predict_probability(scenario_frame)
            records.append(
                {
                    "plan": name,
                    "estimated_gpa_after": estimated_gpa,
                    "probability_after": estimated_probability,
                    "delta_gpa": estimated_gpa - current_gpa,
                    "delta_probability": estimated_probability - current_probability,
                    "effort": int(sum(efforts)),
                    "Absences_plan": float(scenario["Absences"]),
                    "StudyTimeWeekly_plan": float(scenario["StudyTimeWeekly"]),
                    "Tutoring_plan": int(scenario["Tutoring"]),
                    "ParentalSupport_plan": int(scenario["ParentalSupport"]),
                }
            )
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records).sort_values(
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
        probability = self._predict_probability(case)
        plans = self._recommendation_plans(case_series, estimated_gpa, probability)
        if plans.empty:
            return {
                "ok": True,
                "estimated_gpa": round(estimated_gpa, 4),
                "good_performance_probability": round(probability, 4),
                "good_performance_threshold": GOOD_PERFORMANCE_THRESHOLD,
                "risk_level": _risk_level(probability),
                "messages": [
                    "El estudiante ya esta en el maximo de las variables accionables simuladas.",
                    "Mantener asistencia, estudio constante y tutoring es la prioridad.",
                    "Estos resultados son simulaciones del modelo, no una garantia de calificacion.",
                ],
                "recommended_plan": {
                    "plan": "mantener habitos actuales",
                    "estimated_gpa_after": round(estimated_gpa, 4),
                    "probability_after": round(probability, 4),
                    "delta_gpa": 0.0,
                    "delta_probability": 0.0,
                    "effort": 0,
                },
                "top_plans": [],
                "excluded_from_advice": EXCLUDED_FROM_ADVICE,
            }

        best_plan = plans.iloc[0]

        return {
            "ok": True,
            "estimated_gpa": round(estimated_gpa, 4),
            "good_performance_probability": round(probability, 4),
            "good_performance_threshold": GOOD_PERFORMANCE_THRESHOLD,
            "risk_level": _risk_level(probability),
            "messages": _message_for_plan(best_plan),
            "recommended_plan": {
                "plan": best_plan["plan"],
                "estimated_gpa_after": round(float(best_plan["estimated_gpa_after"]), 4),
                "probability_after": round(float(best_plan["probability_after"]), 4),
                "delta_gpa": round(float(best_plan["delta_gpa"]), 4),
                "delta_probability": round(float(best_plan["delta_probability"]), 4),
                "effort": int(best_plan["effort"]),
            },
            "top_plans": [
                {
                    "plan": row["plan"],
                    "estimated_gpa_after": round(float(row["estimated_gpa_after"]), 4),
                    "probability_after": round(float(row["probability_after"]), 4),
                    "delta_gpa": round(float(row["delta_gpa"]), 4),
                    "delta_probability": round(float(row["delta_probability"]), 4),
                    "effort": int(row["effort"]),
                }
                for _, row in plans.head(3).iterrows()
            ],
            "excluded_from_advice": EXCLUDED_FROM_ADVICE,
        }
