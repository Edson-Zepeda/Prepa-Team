# Prepa-Team

Sistema de control escolar demo con intervención académica personalizada.

## Enfoque Del Producto

Prepa-Team no se presenta como un predictor general de éxito académico. Su salida principal es una herramienta de **priorización e intervención escolar**:

- estima el estado actual del alumno en escala mexicana `0-10`
- calcula la probabilidad de mantener buen rendimiento
- detecta factores accionables que empujan el riesgo académico
- propone el cambio mínimo para subir de nivel
- compara planes de mínimo esfuerzo, balanceado y mayor impacto
- genera reportes imprimibles por alumno
- permite carga manual o masiva de calificaciones

## Estructura

```text
Proyecto_GPA.ipynb                 Notebook técnico del modelo
data/raw/student_performance.csv   Dataset base
src/student_success/               Entrenamiento, inferencia y recomendaciones
models/                            Artefactos entrenados del modelo
web/backend/                       FastAPI, SQLite, autenticación y roles
web/frontend/                      Plantillas y estilos del sistema web
docs/API_CONTRACT.md               Contrato estable entre UI y API
examples/                          Ejemplos de request y response
paper/                             Paper en español e inglés, figuras y BibTeX
scripts/build_model_artifacts.py   Reconstrucción de artefactos del modelo
scripts/bootstrap_school_system.py Inicialización de base de datos y usuarios demo
scripts/smoke_test_web_beta.py     Prueba rápida del sistema web
requirements.txt                   Dependencias del proyecto
```

## Instalación

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Sistema Web

```bash
python scripts/build_model_artifacts.py
python scripts/bootstrap_school_system.py
python scripts/smoke_test_web_beta.py
python -m uvicorn web.backend.app:app --reload
```

Abrir en navegador:

```text
http://127.0.0.1:8000
```

Credenciales demo:

```text
admin@prepateam.local / Admin1234!
edson@prepateam.mx / prepateam
francisco@prepateam.mx / prepateam
alan@prepateam.mx / prepateam
```

## Notebook

```bash
jupyter notebook Proyecto_GPA.ipynb
```

También puede abrirse en VS Code y ejecutarse con `Run All`.

## Paper

Para refrescar las figuras:

```bash
python paper/generate_paper_assets.py
```

Para compilar en Overleaf, subir la carpeta `paper/` completa y elegir:

- Español: `Paper_Proyecto_GPA.tex`
- Inglés: `Paper_GPA_English.tex`

## Nota Ética

Las recomendaciones son simulaciones del modelo, no evidencia causal ni garantía de calificación. El sistema no usa `StudentID`, `GradeClass`, `Gender` ni `Ethnicity` para sugerir acciones y no sustituye el criterio de docentes, tutores o directivos.
