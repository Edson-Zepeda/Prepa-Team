# Contrato API para beta web

Base local recomendada:

```text
http://127.0.0.1:8000
```

## Health check

```http
GET /health
```

Respuesta:

```json
{
  "status": "ok"
}
```

## Schema

```http
GET /schema
```

Devuelve campos requeridos, limites permitidos y variables excluidas de recomendaciones.

## Prediccion

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

Response exitosa:

```json
{
  "ok": true,
  "estimated_gpa": 2.2474,
  "good_performance_probability": 0.1502,
  "good_performance_threshold": 2.5,
  "risk_level": "riesgo alto",
  "messages": [
    "Prioriza reducir ausencias: es el factor con mayor impacto en el modelo.",
    "Aumenta tus horas de estudio semanal de forma sostenida.",
    "Activa tutoring para reforzar las areas donde tengas mas dificultad.",
    "Busca mayor seguimiento familiar o de un tutor academico.",
    "Estos resultados son simulaciones del modelo, no una garantia de calificacion."
  ],
  "recommended_plan": {
    "plan": "reducir ausencias en 10 + aumentar estudio hasta 20h/semana + activar tutoring + aumentar apoyo parental en 2 + activar Extracurricular",
    "estimated_gpa_after": 4.0,
    "probability_after": 1.0,
    "delta_gpa": 1.7526,
    "delta_probability": 0.8498,
    "effort": 27
  },
  "top_plans": [
    {
      "plan": "reducir ausencias en 10 + aumentar estudio hasta 20h/semana + activar tutoring + aumentar apoyo parental en 2 + activar Extracurricular",
      "estimated_gpa_after": 4.0,
      "probability_after": 1.0,
      "delta_gpa": 1.7526,
      "delta_probability": 0.8498,
      "effort": 27
    }
  ],
  "excluded_from_advice": [
    "StudentID",
    "GradeClass",
    "Gender",
    "Ethnicity"
  ]
}
```

Response con error de validacion:

```json
{
  "ok": false,
  "errors": [
    {
      "field": "Absences",
      "message": "Debe estar entre 0 y 30."
    }
  ]
}
```

## Campos permitidos

La UI solo debe enviar:

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

La UI no debe pedir ni enviar:

```text
StudentID
GradeClass
Gender
Ethnicity
```

## Rangos

```text
Age: 10 a 25
StudyTimeWeekly: 0 a 20
Absences: 0 a 30
ParentalEducation: 0 a 4
Tutoring: 0 o 1
ParentalSupport: 0 a 4
Extracurricular: 0 o 1
Sports: 0 o 1
Music: 0 o 1
Volunteering: 0 o 1
```
