# Backend Del Sistema Escolar

Backend FastAPI para login, roles, control escolar, reportes y recomendaciones.

## Instalación

Desde la raíz del repo:

```bash
python -m pip install -r requirements.txt
```

## Preparar Modelo

```bash
python scripts/build_model_artifacts.py
```

Esto crea:

```text
models/student_success_artifacts.joblib
models/student_success_metadata.json
```

## Inicializar Base De Datos

```bash
python scripts/bootstrap_school_system.py
```

## Ejecutar

Prueba rápida:

```bash
python scripts/smoke_test_web_beta.py
```

Servidor local:

```bash
python -m uvicorn web.backend.app:app --reload
```

Endpoints principales:

```text
GET  /health
GET  /schema
POST /predict
POST /api/auth/login
POST /api/auth/logout
GET  /api/student/me
POST /api/student/predict
GET  /api/admin/students/{id}/predict
```
