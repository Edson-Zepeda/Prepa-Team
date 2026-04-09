# Contrato API del sistema escolar

Base local recomendada:

```text
http://127.0.0.1:8000
```

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

## Predicción pública

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
  "risk_level": "riesgo moderado",
  "messages": [
    "Reducir ausencias puede subir tu promedio estimado y bajar tu riesgo académico."
  ],
  "recommended_plan": {
    "plan": "reducir ausencias en 10 + aumentar estudio en 5h/semana + activar tutoring",
    "estimated_average_after_10": 7.1,
    "probability_after": 0.88,
    "delta_average_10": 1.48,
    "delta_probability": 0.15,
    "effort": 17
  },
  "top_plans": [],
  "excluded_from_advice": [
    "StudentID",
    "GradeClass",
    "Gender",
    "Ethnicity"
  ]
}
```

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

Usa exactamente los mismos campos del request de predicción.

## Predicción del alumno autenticado

```http
POST /api/student/predict
```

La API toma el perfil guardado del alumno autenticado y devuelve el mismo shape de respuesta que `/predict`.

## Carga manual de calificación

```http
POST /api/admin/grades/manual
Content-Type: application/json
```

Request:

```json
{
  "student_id": 1,
  "subject_name": "Matemáticas",
  "period": "2026-1",
  "grade": 8.7
}
```

Reglas:

- `grade` debe estar entre `0` y `10`
- el estatus se deriva automáticamente:
  - `approved` si `grade >= 6.0`
  - `failed` si `grade < 6.0`

## Importación CSV

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
