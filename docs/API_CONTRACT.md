# Contrato API del sistema escolar

Base local recomendada:

```text
http://127.0.0.1:8000
```

## Posicionamiento del producto

La API publica expone a Prepa-Team como una **herramienta de priorizacion e intervencion escolar personalizada**. La salida principal no es una frase generica, sino planes concretos para mover al alumno a una zona aceptable con el menor cambio posible.

Nota sobre variables parentales:

- `ParentalEducation` sigue entrando al modelo como escala ordinal, pero no debe mostrarse como recomendacion directa al alumno.
- `ParentalSupport` tambien entra como escala ordinal `0-4`, pero en interfaz y mensajes debe traducirse a niveles cualitativos: `muy bajo`, `bajo`, `medio`, `alto`, `muy alto`.

## Rutas generales

```http
GET /health
GET /schema
POST /predict
POST /api/auth/login
POST /api/auth/logout
GET /api/student/me
PUT /api/student/profile
POST /api/student/predict
GET /api/admin/students/{id}/predict
POST /api/admin/students
POST /api/admin/grades/manual
POST /api/admin/grades/import
```

## Rutas web utiles

```http
GET /student/report
GET /admin/students/{id}/report
GET /admin/grades/template.csv
```

- `/student/report`: vista imprimible del alumno autenticado.
- `/admin/students/{id}/report`: reporte imprimible del alumno para directivos.
- `/admin/grades/template.csv`: plantilla base para la carga masiva.

## Esquema publico

```http
GET /schema
```

Campos clave esperados:

- `good_performance_threshold_10 = 6.0`
- `acceptable_zone = "medio"`
- `risk_bands`
- `plan_strategies = ["minimo_esfuerzo", "balanceado", "mayor_impacto"]`

## Prediccion publica

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

Response:

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
    "why_selected": "Se eligio porque permite subir de nivel con el menor ajuste posible."
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
    "why_selected": "Se eligio porque alcanza la zona medio con el menor esfuerzo total."
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
    "Estado actual: promedio estimado 5.6/10, probabilidad de buen rendimiento 73% y nivel alto."
  ],
  "excluded_from_advice": [
    "StudentID",
    "GradeClass",
    "Gender",
    "Ethnicity"
  ]
}
```

## Reglas de negocio del plan

- `recommended_plan`
  - si el alumno esta en `alto` o `muy alto`, intenta llegar a `medio` o mejor
  - si el alumno esta en `medio`, intenta llegar a `bajo`
  - si ya esta en `bajo`, prioriza mantenimiento o mejora ligera
- `next_level_plan`
  - busca el menor cambio para subir solo un nivel
- `top_plans`
  - devuelve exactamente 3 estrategias: `minimo_esfuerzo`, `balanceado`, `mayor_impacto`

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

## Perfil del alumno

```http
PUT /api/student/profile
Content-Type: application/json
```

Usa exactamente los mismos campos del request de prediccion.

## Prediccion del alumno autenticado

```http
POST /api/student/predict
```

La API toma el perfil guardado del alumno autenticado y devuelve el mismo shape de respuesta que `/predict`.

## Carga manual de calificacion

```http
POST /api/admin/grades/manual
Content-Type: application/json
```

Request:

```json
{
  "student_id": 1,
  "subject_name": "Matematicas",
  "period": "2026-1",
  "grade": 8.7
}
```

Reglas:

- `grade` debe estar entre `0` y `10`
- el estatus se deriva automaticamente:
  - `approved` si `grade >= 6.0`
  - `failed` si `grade < 6.0`

## Importacion CSV

```http
POST /api/admin/grades/import
Content-Type: multipart/form-data
```

Schema fijo:

```text
student_code,full_name,subject_name,period,grade
```

## Campos permitidos para recomendaciones

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

No deben enviarse:

```text
StudentID
GradeClass
Gender
Ethnicity
```
