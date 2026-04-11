# Contrato API Del Sistema Escolar

Base local recomendada:

```text
http://127.0.0.1:8000
```

## Posicionamiento

La API expone a Prepa-Team como una **herramienta de priorización e intervención escolar personalizada**. La salida principal no es una recomendación genérica, sino un conjunto de planes concretos para mover al alumno a una zona académica aceptable con el menor cambio posible.

Las recomendaciones son simulaciones del modelo. No representan causalidad ni garantía de calificación.

## Rutas Principales

```http
GET  /health
GET  /schema
POST /predict
POST /api/auth/login
POST /api/auth/logout
GET  /api/student/me
PUT  /api/student/profile
POST /api/student/predict
GET  /api/admin/students/{id}/predict
POST /api/admin/students
POST /api/admin/grades/manual
POST /api/admin/grades/import
GET  /student/report
GET  /admin/students/{id}/report
GET  /admin/grades/template.csv
```

## Esquema Público

```http
GET /schema
```

Campos clave:

- `good_performance_threshold_10 = 6.0`
- `acceptable_zone = "medio"`
- `risk_bands`
- `plan_strategies = ["minimo_esfuerzo", "balanceado", "mayor_impacto"]`

## Predicción Pública

```http
POST /predict
Content-Type: application/json
```

Request:

```json
{
  "Age": 17,
  "StudyTimeWeekly": 8,
  "Absences": 10,
  "ParentalEducation": 2,
  "Tutoring": 0,
  "ParentalSupport": 2,
  "Extracurricular": 0,
  "Sports": 1,
  "Music": 0,
  "Volunteering": 0
}
```

Response esperado:

```json
{
  "ok": true,
  "estimated_average_10": 5.62,
  "good_performance_probability": 0.73,
  "good_performance_threshold_10": 6.0,
  "risk_level": "alto",
  "priority_factors": [
    {
      "field": "Absences",
      "label": "ausencias",
      "change_text": "Reducir ausencias de 10 a 5",
      "delta_probability": 0.18,
      "delta_average_10": 0.42
    }
  ],
  "next_level_plan": {
    "strategy": "siguiente_nivel",
    "title": "Cambio mínimo",
    "target_zone": "medio",
    "plan": "Reducir ausencias de 10 a 5 + Aumentar horas de estudio de 8 h a 10 h por semana",
    "actions": [
      {
        "field": "Absences",
        "label": "ausencias",
        "from": 10,
        "to": 5,
        "change_text": "Reducir ausencias de 10 a 5"
      }
    ],
    "estimated_average_after_10": 6.3,
    "probability_after": 0.56,
    "delta_average_10": 0.68,
    "delta_probability": 0.19,
    "effort_score": 7,
    "effort_label": "medio",
    "why_selected": "Se eligió porque permite subir de nivel con el menor ajuste posible."
  },
  "recommended_plan": {
    "strategy": "minimo_esfuerzo",
    "title": "Plan principal",
    "target_zone": "medio",
    "plan": "Reducir ausencias de 10 a 5 + Aumentar horas de estudio de 8 h a 10 h por semana",
    "actions": [
      {
        "field": "Absences",
        "label": "ausencias",
        "from": 10,
        "to": 5,
        "change_text": "Reducir ausencias de 10 a 5"
      }
    ],
    "estimated_average_after_10": 6.3,
    "probability_after": 0.56,
    "delta_average_10": 0.68,
    "delta_probability": 0.19,
    "effort_score": 7,
    "effort_label": "medio",
    "why_selected": "Se eligió porque alcanza la zona media con el menor esfuerzo total."
  },
  "top_plans": [
    {
      "strategy": "minimo_esfuerzo",
      "title": "Plan de mínimo esfuerzo"
    },
    {
      "strategy": "balanceado",
      "title": "Plan balanceado"
    },
    {
      "strategy": "mayor_impacto",
      "title": "Plan de mayor impacto"
    }
  ],
  "messages": [
    "Estado actual: promedio estimado 5.6/10, probabilidad de buen rendimiento 73% y riesgo alto."
  ],
  "excluded_from_advice": [
    "StudentID",
    "GradeClass",
    "Gender",
    "Ethnicity"
  ]
}
```

## Reglas Del Plan

- `recommended_plan`: plan principal para llegar a la zona objetivo.
- `next_level_plan`: menor cambio para subir solo un nivel de riesgo.
- `top_plans`: tres estrategias únicas: mínimo esfuerzo, balanceado y mayor impacto.
- Si el alumno ya está en riesgo bajo, el sistema debe priorizar mantenimiento o mejora ligera.

## Login

```http
POST /api/auth/login
Content-Type: application/json
```

Request:

```json
{
  "email": "admin@prepateam.local",
  "password": "Admin1234!"
}
```

Response:

```json
{
  "ok": true,
  "role": "admin",
  "redirect_to": "/admin/dashboard"
}
```

## Carga De Calificaciones

Carga manual:

```http
POST /api/admin/grades/manual
Content-Type: application/json
```

```json
{
  "student_id": 1,
  "subject_name": "Matemáticas",
  "period": "2026-1",
  "grade": 8.7
}
```

Carga masiva:

```http
POST /api/admin/grades/import
Content-Type: multipart/form-data
```

Schema CSV:

```text
student_code,full_name,subject_name,period,grade
```

Reglas:

- `grade` debe estar entre `0` y `10`.
- `approved` si `grade >= 6.0`.
- `failed` si `grade < 6.0`.

## Variables

Campos permitidos para recomendaciones:

```text
Age
StudyTimeWeekly
Absences
ParentalEducation
Tutoring
ParentalSupport
Extracurricular
Sports
Music
Volunteering
```

Campos excluidos:

```text
StudentID
GradeClass
Gender
Ethnicity
```

Nota: `ParentalEducation` y `ParentalSupport` entran al modelo como escalas ordinales, pero en interfaz deben mostrarse con etiquetas cualitativas cuando sea posible.
