from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .config import (
    ACTIONABLE_FEATURES,
    ADVICE_FEATURES,
    ARTIFACT_PATH,
    EXCLUDED_FROM_ADVICE,
    FIELD_LIMITS,
    GOOD_PERFORMANCE_THRESHOLD_10,
    MEXICAN_SCALE_FACTOR,
)
from .training import save_artifacts


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


RISK_BANDS = [
    {"label": "muy alto", "min_probability": 0.0, "max_probability": 0.2499},
    {"label": "alto", "min_probability": 0.25, "max_probability": 0.4999},
    {"label": "medio", "min_probability": 0.50, "max_probability": 0.7499},
    {"label": "bajo", "min_probability": 0.75, "max_probability": 1.0},
]
RISK_SCORES = {band["label"]: index for index, band in enumerate(RISK_BANDS)}
PLAN_STRATEGIES = ["minimo_esfuerzo", "balanceado", "mayor_impacto"]

FIELD_LABELS = {
    "Age": "edad",
    "StudyTimeWeekly": "horas de estudio",
    "Absences": "ausencias",
    "ParentalEducation": "educacion parental",
    "Tutoring": "tutoria",
    "ParentalSupport": "apoyo parental",
    "Extracurricular": "actividad extracurricular",
    "Sports": "deportes",
    "Music": "musica",
    "Volunteering": "voluntariado",
    "Activities": "actividades",
}

ACTIVITY_FIELDS = ["Extracurricular", "Sports", "Music", "Volunteering"]
ACTIVITY_LABELS = {field: FIELD_LABELS[field] for field in ACTIVITY_FIELDS}


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


def _effort_label(score: int) -> str:
    if score <= 2:
        return "bajo"
    if score <= 6:
        return "bajo-medio"
    if score <= 10:
        return "medio"
    return "alto"


def _target_zone_for_level(level: str) -> str:
    if level in {"muy alto", "alto"}:
        return "medio"
    return "bajo"


def _plan_name(parts: list[str]) -> str:
    chosen = [part for part in parts if not part.startswith("mantener")]
    return " + ".join(chosen) if chosen else "sin cambios"


def _value_to_display(field: str, value: float | int) -> str | float | int:
    if field in {"Tutoring", "Extracurricular", "Sports", "Music", "Volunteering"}:
        return "Si" if int(value) == 1 else "No"
    if field == "StudyTimeWeekly":
        if float(value).is_integer():
            return f"{int(value)} h"
        return f"{float(value):.1f} h"
    return int(value) if float(value).is_integer() else round(float(value), 1)


def _change_text(field: str, before: float | int, after: float | int) -> str:
    if field == "Absences":
        return f"Reducir ausencias de {int(before)} a {int(after)}"
    if field == "StudyTimeWeekly":
        return f"Aumentar horas de estudio de {_value_to_display(field, before)} a {_value_to_display(field, after)} por semana"
    if field == "Tutoring":
        return "Activar tutoria"
    if field == "ParentalSupport":
        return f"Subir apoyo parental de {int(before)} a {int(after)}"
    if field in ACTIVITY_FIELDS:
        return f"Activar {FIELD_LABELS[field]}"
    return f"Ajustar {FIELD_LABELS[field]} de {_value_to_display(field, before)} a {_value_to_display(field, after)}"


def _maintenance_plan(
    estimated_average_10: float,
    probability: float,
    title: str = "Plan de mantenimiento",
) -> dict[str, Any]:
    return {
        "strategy": "minimo_esfuerzo",
        "title": title,
        "target_zone": "bajo",
        "risk_level_after": "bajo",
        "plan": "Mantener habitos actuales",
        "actions": [
            {
                "field": "maintenance",
                "label": "mantenimiento",
                "from": "-",
                "to": "-",
                "change_text": "Mantener asistencia, estudio constante y seguimiento academico.",
            }
        ],
        "estimated_average_after_10": round(estimated_average_10, 2),
        "probability_after": round(probability, 4),
        "delta_average_10": 0.0,
        "delta_probability": 0.0,
        "effort_score": 0,
        "effort_label": "bajo",
        "why_selected": "No se detecto una mejora material con cambios pequenos, por lo que la prioridad es sostener los habitos actuales.",
    }


class StudentSuccessService:
    """Prediction and intervention facade for the school control web app."""

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
            "good_performance_threshold_10": GOOD_PERFORMANCE_THRESHOLD_10,
            "mexican_scale_factor": MEXICAN_SCALE_FACTOR,
            "acceptable_zone": "medio",
            "risk_bands": RISK_BANDS,
            "plan_strategies": PLAN_STRATEGIES,
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

    def _predict_gpa_batch(self, cases: pd.DataFrame) -> np.ndarray:
        predictions = self.advice_regressor.predict(cases)
        return np.clip(np.asarray(predictions, dtype=float), 0, 4)

    def _predict_probability(self, case: pd.DataFrame) -> float:
        return float(self.good_performance_classifier.predict_proba(case)[0, 1])

    def _predict_probability_batch(self, cases: pd.DataFrame) -> np.ndarray:
        probabilities = self.good_performance_classifier.predict_proba(cases)[:, 1]
        return np.asarray(probabilities, dtype=float)

    def _intervention_options(self, case: pd.Series) -> dict[str, list[tuple[str, int, Any]]]:
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
        for increase in [2, 3, 5, 8]:
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
        for activity in ACTIVITY_FIELDS:
            if int(case[activity]) == 0:
                activity_options.append(
                    (
                        f"activar {ACTIVITY_LABELS[activity]}",
                        1,
                        lambda x, a=activity: x.__setitem__(a, 1),
                    )
                )

        return {
            "absences": absence_options,
            "study": study_options,
            "tutoring": tutoring_options,
            "support": support_options,
            "activities": activity_options,
        }

    def _build_actions(self, current_case: pd.Series, scenario_row: pd.Series) -> list[dict[str, Any]]:
        actions = []
        for field in ACTIONABLE_FEATURES:
            before = current_case[field]
            after = scenario_row[field]
            if float(before) == float(after):
                continue
            actions.append(
                {
                    "field": field,
                    "label": FIELD_LABELS[field],
                    "from": _value_to_display(field, before),
                    "to": _value_to_display(field, after),
                    "change_text": _change_text(field, before, after),
                }
            )
        return actions

    def _recommendation_plans(self, case: pd.Series, current_gpa: float, current_probability: float) -> pd.DataFrame:
        option_groups = self._intervention_options(case)
        scenarios: list[dict[str, Any]] = []
        for option_combo in product(*option_groups.values()):
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
                    **{feature: scenario[feature] for feature in ADVICE_FEATURES},
                }
            )
        if not scenarios:
            return pd.DataFrame()

        scenario_frame = pd.DataFrame(scenarios)
        model_frame = scenario_frame[ADVICE_FEATURES]
        gpa_predictions = self._predict_gpa_batch(model_frame)
        probability_predictions = self._predict_probability_batch(model_frame)

        result = scenario_frame.copy()
        result["estimated_gpa_after"] = gpa_predictions
        result["estimated_average_after_10"] = np.clip(gpa_predictions * MEXICAN_SCALE_FACTOR, 0, 10)
        result["probability_after"] = probability_predictions
        result["risk_level_after"] = [
            _risk_level(probability_after) for probability_after in result["probability_after"].tolist()
        ]
        result["risk_score_after"] = result["risk_level_after"].map(RISK_SCORES)
        result["delta_gpa"] = result["estimated_gpa_after"] - current_gpa
        result["delta_average_10"] = result["estimated_average_after_10"] - _gpa_to_average_10(current_gpa)
        result["delta_probability"] = result["probability_after"] - current_probability
        result["balance_score"] = result["delta_probability"] / result["effort"].clip(lower=1)
        return result.reset_index(drop=True)

    def _priority_factors(
        self,
        case: pd.Series,
        current_gpa: float,
        current_probability: float,
    ) -> list[dict[str, Any]]:
        option_groups = self._intervention_options(case)
        factor_map = [
            ("Absences", "ausencias", "absences"),
            ("StudyTimeWeekly", "horas de estudio", "study"),
            ("Tutoring", "tutoria", "tutoring"),
            ("ParentalSupport", "apoyo parental", "support"),
            ("Activities", "actividades", "activities"),
        ]
        single_scenarios: list[dict[str, Any]] = []
        for factor_key, factor_label, option_group in factor_map:
            for option_name, effort, mutator in option_groups[option_group]:
                if effort == 0:
                    continue
                scenario = case.copy()
                mutator(scenario)
                single_scenarios.append(
                    {
                        "factor": factor_key,
                        "label": factor_label,
                        "option_name": option_name,
                        "effort": int(effort),
                        **{feature: scenario[feature] for feature in ADVICE_FEATURES},
                    }
                )

        if not single_scenarios:
            return []

        scenario_frame = pd.DataFrame(single_scenarios)
        gpa_predictions = self._predict_gpa_batch(scenario_frame[ADVICE_FEATURES])
        probability_predictions = self._predict_probability_batch(scenario_frame[ADVICE_FEATURES])
        scenario_frame["estimated_average_after_10"] = np.clip(gpa_predictions * MEXICAN_SCALE_FACTOR, 0, 10)
        scenario_frame["delta_average_10"] = scenario_frame["estimated_average_after_10"] - _gpa_to_average_10(current_gpa)
        scenario_frame["delta_probability"] = probability_predictions - current_probability

        best_rows: list[dict[str, Any]] = []
        for factor_key, factor_label, _ in factor_map:
            factor_rows = scenario_frame[scenario_frame["factor"] == factor_key].copy()
            if factor_rows.empty:
                best_rows.append(
                    {
                        "field": factor_key,
                        "label": factor_label,
                        "change_text": f"Mantener {factor_label}",
                        "delta_probability": 0.0,
                        "delta_average_10": 0.0,
                    }
                )
                continue
            factor_rows = factor_rows.sort_values(
                ["delta_probability", "delta_average_10", "effort"],
                ascending=[False, False, True],
            )
            row = factor_rows.iloc[0]
            actions = self._build_actions(case, row)
            best_rows.append(
                {
                    "field": factor_key,
                    "label": factor_label,
                    "change_text": actions[0]["change_text"] if actions else f"Mantener {factor_label}",
                    "delta_probability": round(float(row["delta_probability"]), 4),
                    "delta_average_10": round(float(row["delta_average_10"]), 2),
                }
            )

        ordered = sorted(
            best_rows,
            key=lambda item: (item["delta_probability"], item["delta_average_10"]),
            reverse=True,
        )
        return ordered[:3]

    def _select_plan(self, pool: pd.DataFrame, strategy: str) -> pd.Series | None:
        if pool.empty:
            return None
        if strategy == "minimo_esfuerzo":
            ranked = pool.sort_values(
                ["effort", "delta_probability", "delta_average_10"],
                ascending=[True, False, False],
            )
            return ranked.iloc[0]
        if strategy == "balanceado":
            ranked = pool.sort_values(
                ["balance_score", "delta_average_10", "delta_probability", "effort"],
                ascending=[False, False, False, True],
            )
            return ranked.iloc[0]
        ranked = pool.sort_values(
            ["delta_probability", "delta_average_10", "effort"],
            ascending=[False, False, True],
        )
        return ranked.iloc[0]

    def _why_selected(self, strategy: str, priority_factors: list[dict[str, Any]], target_zone: str) -> str:
        factor_text = ", ".join(factor["label"] for factor in priority_factors[:2]) or "ausencias y horas de estudio"
        if strategy == "minimo_esfuerzo":
            return f"Se eligio porque alcanza la zona {target_zone} con el menor esfuerzo total. En este caso, {factor_text} son los factores mas influyentes."
        if strategy == "balanceado":
            return f"Se eligio porque ofrece la mejor relacion entre impacto esperado y esfuerzo. En este caso, {factor_text} son los factores mas influyentes."
        if strategy == "mayor_impacto":
            return f"Se eligio porque produce la mayor mejora esperada. En este caso, {factor_text} son los factores mas influyentes."
        return f"Se eligio porque permite subir de nivel con el menor ajuste posible. En este caso, {factor_text} son los factores mas influyentes."

    def _format_plan(
        self,
        row: pd.Series,
        strategy: str,
        title: str,
        current_case: pd.Series,
        current_average_10: float,
        current_probability: float,
        priority_factors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        actions = self._build_actions(current_case, row)
        plan_text = " + ".join(action["change_text"] for action in actions) if actions else "Mantener habitos actuales"
        target_zone = str(row["risk_level_after"])
        return {
            "strategy": strategy,
            "title": title,
            "target_zone": target_zone,
            "risk_level_after": target_zone,
            "plan": plan_text,
            "actions": actions or _maintenance_plan(current_average_10, current_probability)["actions"],
            "estimated_average_after_10": round(float(row["estimated_average_after_10"]), 2),
            "probability_after": round(float(row["probability_after"]), 4),
            "delta_average_10": round(float(row["delta_average_10"]), 2),
            "delta_probability": round(float(row["delta_probability"]), 4),
            "effort_score": int(row["effort"]),
            "effort_label": _effort_label(int(row["effort"])),
            "why_selected": self._why_selected(strategy, priority_factors, target_zone),
        }

    def _build_messages(
        self,
        current_average_10: float,
        probability: float,
        current_level: str,
        priority_factors: list[dict[str, Any]],
        recommended_plan: dict[str, Any],
        next_level_plan: dict[str, Any] | None,
    ) -> list[str]:
        factor_text = ", ".join(factor["label"] for factor in priority_factors)
        messages = [
            f"Estado actual: promedio estimado {current_average_10:.1f}/10, probabilidad de buen rendimiento {_display_probability(probability)} y nivel {current_level}.",
            f"Factores prioritarios: {factor_text}.",
        ]
        if current_level == "bajo":
            messages.append(
                f"Plan principal: {recommended_plan['plan']}. Mantiene el nivel bajo con esfuerzo {recommended_plan['effort_label']}."
            )
        else:
            if next_level_plan:
                messages.append(
                    f"Plan minimo para subir de nivel: {next_level_plan['plan']}. Lleva a {next_level_plan['target_zone']} con esfuerzo {next_level_plan['effort_label']}."
                )
            messages.append(
                f"Plan principal para llegar a zona aceptable: {recommended_plan['plan']}. Impacto esperado: +{recommended_plan['delta_average_10']:.2f} puntos y +{recommended_plan['delta_probability'] * 100:.1f} puntos porcentuales."
            )
        messages.append("Planes alternativos: revisa minimo esfuerzo, balanceado y mayor impacto segun tus recursos.")
        messages.append(f"Por que se eligio este plan: {recommended_plan['why_selected']}")
        messages.append(
            "Las recomendaciones son simulaciones del modelo y sirven como apoyo para priorizar intervenciones escolares."
        )
        return messages

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
        current_level = _risk_level(probability)
        current_score = RISK_SCORES[current_level]
        target_zone = _target_zone_for_level(current_level)
        target_score = RISK_SCORES[target_zone]

        plans = self._recommendation_plans(case_series, estimated_gpa, probability)
        priority_factors = self._priority_factors(case_series, estimated_gpa, probability)

        if plans.empty:
            maintenance = _maintenance_plan(estimated_average_10, probability)
            return {
                "ok": True,
                "estimated_average_10": round(estimated_average_10, 2),
                "good_performance_probability": round(probability, 4),
                "good_performance_threshold_10": GOOD_PERFORMANCE_THRESHOLD_10,
                "risk_level": current_level,
                "priority_factors": priority_factors,
                "next_level_plan": None,
                "messages": self._build_messages(
                    estimated_average_10,
                    probability,
                    current_level,
                    priority_factors,
                    maintenance,
                    None,
                ),
                "recommended_plan": maintenance,
                "top_plans": [
                    {**maintenance, "strategy": "minimo_esfuerzo", "title": "Plan de mantenimiento"},
                    {**maintenance, "strategy": "balanceado", "title": "Plan balanceado"},
                    {**maintenance, "strategy": "mayor_impacto", "title": "Plan de mayor impacto"},
                ],
                "excluded_from_advice": EXCLUDED_FROM_ADVICE,
            }

        if current_level == "bajo":
            light_pool = plans[
                (plans["effort"] <= 3)
                & ((plans["delta_probability"] >= 0.01) | (plans["delta_average_10"] >= 0.10))
            ]
            strategy_pool = light_pool if not light_pool.empty else plans.nsmallest(min(10, len(plans)), "effort")
            recommended_row = self._select_plan(strategy_pool, "minimo_esfuerzo")
            next_level_plan = None
        else:
            next_score = min(current_score + 1, max(RISK_SCORES.values()))
            exact_next_pool = plans[plans["risk_score_after"] == next_score]
            improved_pool = plans[plans["risk_score_after"] >= next_score]
            next_pool = exact_next_pool if not exact_next_pool.empty else improved_pool
            next_level_row = self._select_plan(next_pool, "minimo_esfuerzo")
            next_level_plan = (
                self._format_plan(
                    next_level_row,
                    "siguiente_nivel",
                    "Cambio minimo al siguiente nivel",
                    case_series,
                    estimated_average_10,
                    probability,
                    priority_factors,
                )
                if next_level_row is not None
                else None
            )

            target_pool = plans[plans["risk_score_after"] >= target_score]
            strategy_pool = target_pool if not target_pool.empty else (next_pool if not next_pool.empty else plans)
            recommended_row = self._select_plan(strategy_pool, "minimo_esfuerzo")

        if recommended_row is None:
            maintenance = _maintenance_plan(estimated_average_10, probability)
            return {
                "ok": True,
                "estimated_average_10": round(estimated_average_10, 2),
                "good_performance_probability": round(probability, 4),
                "good_performance_threshold_10": GOOD_PERFORMANCE_THRESHOLD_10,
                "risk_level": current_level,
                "priority_factors": priority_factors,
                "next_level_plan": next_level_plan,
                "messages": self._build_messages(
                    estimated_average_10,
                    probability,
                    current_level,
                    priority_factors,
                    maintenance,
                    next_level_plan,
                ),
                "recommended_plan": maintenance,
                "top_plans": [
                    {**maintenance, "strategy": "minimo_esfuerzo", "title": "Plan minimo"},
                    {**maintenance, "strategy": "balanceado", "title": "Plan balanceado"},
                    {**maintenance, "strategy": "mayor_impacto", "title": "Plan de mayor impacto"},
                ],
                "excluded_from_advice": EXCLUDED_FROM_ADVICE,
            }

        recommended_title = (
            "Plan de mantenimiento" if current_level == "bajo" else "Plan principal para llegar a zona aceptable"
        )
        recommended_plan = self._format_plan(
            recommended_row,
            "minimo_esfuerzo",
            recommended_title,
            case_series,
            estimated_average_10,
            probability,
            priority_factors,
        )

        top_plans = []
        for strategy, title in [
            ("minimo_esfuerzo", "Plan de minimo esfuerzo"),
            ("balanceado", "Plan balanceado"),
            ("mayor_impacto", "Plan de mayor impacto"),
        ]:
            selected_row = self._select_plan(strategy_pool, strategy)
            if selected_row is None:
                top_plans.append({**recommended_plan, "strategy": strategy, "title": title})
                continue
            top_plans.append(
                self._format_plan(
                    selected_row,
                    strategy,
                    title,
                    case_series,
                    estimated_average_10,
                    probability,
                    priority_factors,
                )
            )

        return {
            "ok": True,
            "estimated_average_10": round(estimated_average_10, 2),
            "good_performance_probability": round(probability, 4),
            "good_performance_threshold_10": GOOD_PERFORMANCE_THRESHOLD_10,
            "risk_level": current_level,
            "priority_factors": priority_factors,
            "next_level_plan": next_level_plan,
            "messages": self._build_messages(
                estimated_average_10,
                probability,
                current_level,
                priority_factors,
                recommended_plan,
                next_level_plan,
            ),
            "recommended_plan": recommended_plan,
            "top_plans": top_plans,
            "excluded_from_advice": EXCLUDED_FROM_ADVICE,
        }
