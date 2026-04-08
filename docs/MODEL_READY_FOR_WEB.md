# Estado del modelo para web beta

## Ya esta listo

- Modelo de regresion para estimar `GPA`.
- Clasificador calibrado para estimar probabilidad de `GPA >= 2.5`.
- Motor de recomendaciones con simulacion de planes de mejora.
- Exclusion de variables no accionables o sensibles en recomendaciones: `StudentID`, `GradeClass`, `Gender`, `Ethnicity`.
- Validacion basica de campos.
- Artefactos serializados en `models/`.
- API minima con FastAPI en `web/backend/app.py`.
- Ejemplos de request/response en `examples/`.

## No se debe prometer

- No garantiza calificaciones.
- No prueba causalidad.
- No reemplaza a un tutor o docente.
- No debe usarse para sancionar estudiantes.

## Mensaje recomendado para la web

```text
Esta herramienta es un simulador academico. Estima escenarios de mejora a partir de un modelo entrenado con datos historicos. No garantiza calificaciones ni sustituye la orientacion de docentes o tutores.
```

## Archivos clave para el equipo web

```text
web/backend/app.py
web/backend/README.md
web/frontend/index.html
web/frontend/README.md
docs/API_CONTRACT.md
examples/student_payload.json
examples/student_response.json
models/student_success_artifacts.joblib
models/student_success_metadata.json
scripts/smoke_test_web_beta.py
```

## Comando rapido de backend

```bash
python scripts/smoke_test_web_beta.py
uvicorn web.backend.app:app --reload
```

Luego abrir:

```text
http://127.0.0.1:8000/docs
```
