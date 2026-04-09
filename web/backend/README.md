# Backend del sistema escolar

Backend FastAPI para login, roles, control escolar y recomendaciones.

## Instalar

Desde la raiz del repo:

```bash
pip install -r requirements.txt
```

## Preparar modelo

```bash
python scripts/build_model_artifacts.py
```

Esto crea:

```text
models/student_success_artifacts.joblib
models/student_success_metadata.json
```

## Inicializar base de datos y admin

```bash
python scripts/bootstrap_school_system.py
```

## Ejecutar API

Prueba rapida:

```bash
python scripts/smoke_test_web_beta.py
```

Servidor local:

```bash
python -m uvicorn web.backend.app:app --reload
```

Endpoints:

```text
GET  /health
GET  /schema
POST /predict
POST /api/auth/login
POST /api/auth/logout
POST /api/student/predict
GET  /api/student/me
GET  /api/admin/students/{id}/predict
```
