# Guia de ramas para la beta web

Todo lo complejo ya esta listo en el repo: entrenamiento, artefactos del modelo, reglas de recomendacion, API base y un HTML inicial. El trabajo del equipo es solo cerrar una beta funcional con frontend y backend reducido.

La beta debe presentarse como herramienta de priorizacion e intervencion escolar. No debe prometer ni garantizar calificaciones.

## Ramas

```text
main                      Rama estable
dev/web-beta              Rama de integracion
feature/francisco-student-ui
feature/alan-model-api
```

Regla: nadie trabaja directo en `main`. Cada quien hace push a su rama y abre PR hacia `dev/web-beta`.

## Francisco: frontend

Rama:

```bash
git fetch origin
git checkout feature/francisco-student-ui
git pull origin feature/francisco-student-ui
```

Archivos base:

```text
web/frontend/index.html
web/frontend/README.md
docs/API_CONTRACT.md
```

Lo que si debe hacer:

- mejorar formulario y vista de resultados
- mostrar `estimated_average_10`, `good_performance_probability`, `risk_level`, `priority_factors`, `next_level_plan`, `recommended_plan` y `top_plans`
- presentar acciones concretas con magnitud, no consejos genericos
- manejar carga y errores de la API
- dejar la vista usable en laptop y celular

Lo que no debe pedir:

```text
StudentID
GradeClass
Gender
Ethnicity
```

Entrega:

```bash
git add .
git commit -m "Improve beta student UI"
git push -u origin feature/francisco-student-ui
```

## Alan: backend reducido

Rama:

```bash
git fetch origin
git checkout feature/alan-model-api
git pull origin feature/alan-model-api
```

Archivos base:

```text
web/backend/app.py
src/student_success/
models/
examples/
docs/API_CONTRACT.md
```

Lo que si debe hacer:

- mantener estable `GET /health`, `GET /schema` y `POST /predict`
- ajustar CORS si el frontend usa otro puerto
- validar entradas y devolver errores claros
- correr `python scripts/smoke_test_web_beta.py` antes de cada PR

Payload permitido:

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

Entrega:

```bash
git add .
git commit -m "Adjust beta model API"
git push -u origin feature/alan-model-api
```

## Criterio de beta lista

- el formulario captura datos sin variables sensibles
- la API responde con JSON estable
- la UI muestra promedio estimado, probabilidad, factores prioritarios y planes de intervencion
- hay minimo dos casos demo probados de punta a punta
- el merge final entra a `dev/web-beta` y luego a `main`
