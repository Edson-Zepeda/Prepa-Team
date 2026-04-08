# Prepa-Team

Prediccion y analisis de rendimiento academico mediante inteligencia artificial. El repositorio contiene solo cuatro piezas: notebook de trabajo, paquete reutilizable del modelo, beta web minima y paper en LaTeX.

## Estructura

```text
Proyecto_GPA.ipynb                 Notebook principal y presentacion tecnica
data/raw/student_performance.csv   Dataset base
src/student_success/               Entrenamiento, inferencia y recomendaciones
models/                            Artefactos listos para la beta web
web/backend/                       API FastAPI minima
web/frontend/                      Frontend beta basico
docs/API_CONTRACT.md               Contrato estable entre UI y API
docs/WEB_BETA_BRANCHING_GUIDE.md   Ramas y responsabilidades del equipo web
paper/                             Paper en espanol e ingles, figuras y BibTeX
scripts/build_model_artifacts.py   Rebuild de artefactos del modelo
scripts/smoke_test_web_beta.py     Prueba rapida de la API beta
requirements.txt                   Dependencias del proyecto
```

## Notebook

```bash
pip install -r requirements.txt
jupyter notebook Proyecto_GPA.ipynb
```

Tambien puede abrirse en VS Code y ejecutarse con `Run All`.

## Beta web

```bash
pip install -r requirements.txt
python scripts/build_model_artifacts.py
python scripts/smoke_test_web_beta.py
uvicorn web.backend.app:app --reload
```

Abrir:

```text
http://127.0.0.1:8000/docs
```

La UI demo base esta en:

```text
web/frontend/index.html
```

## Paper

Para refrescar las figuras usadas por el paper:

```bash
python paper/generate_paper_assets.py
```

Para compilar en Overleaf:

1. Sube la carpeta `paper/` completa.
2. Elige el archivo principal:
   - Espanol: `Paper_Proyecto_GPA.tex`
   - Ingles: `Paper_GPA_English.tex`
3. Compila con BibTeX.

## Nota etica

Las recomendaciones son simulaciones del modelo. No se usan `StudentID`, `GradeClass`, `Gender` ni `Ethnicity` para sugerir acciones y la herramienta no debe presentarse como garantia de calificacion.
