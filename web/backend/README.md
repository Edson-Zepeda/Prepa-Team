# Backend beta

Backend reducido para que la web pueda pedir predicciones y recomendaciones.

## Instalar

Desde la raiz del repo:

```bash
pip install -r requirements.txt
```

## Generar modelo

```bash
python scripts/build_model_artifacts.py
```

Esto crea:

```text
models/student_success_artifacts.joblib
models/student_success_metadata.json
```

Si no existen, la API intenta generarlos automaticamente al primer request.

## Ejecutar API

Prueba rapida:

```bash
python scripts/smoke_test_web_beta.py
```

Servidor local:

```bash
uvicorn web.backend.app:app --reload
```

Endpoints:

```text
GET  /health
GET  /schema
POST /predict
```

## Ejemplo

```bash
curl -X POST http://127.0.0.1:8000/predict ^
  -H "Content-Type: application/json" ^
  -d @examples/student_payload.json
```
