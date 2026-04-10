# Prepa-Team

Repositorio del proyecto y del sistema de control escolar demo.

## Enfoque del producto

Prepa-Team no se presenta como un predictor general de exito academico. Su salida principal es un sistema de **priorizacion e intervencion escolar personalizada**:

- estima el estado actual del alumno en escala mexicana 0-10
- calcula la probabilidad de mantener un buen rendimiento
- detecta los factores accionables que mas empujan el riesgo
- propone el cambio minimo para subir de nivel
- compara planes de minimo esfuerzo, balanceado y mayor impacto
- genera un reporte imprimible por alumno
- permite descargar una plantilla CSV para importacion masiva

## Estructura

```text
Proyecto_GPA.ipynb                 Notebook principal y presentacion tecnica
data/raw/student_performance.csv   Dataset base
src/student_success/               Entrenamiento, inferencia y recomendaciones
models/                            Artefactos del modelo
web/backend/                       FastAPI, SQLite, auth, roles y control escolar
web/frontend/                      Plantillas y estilos del sistema web
docs/API_CONTRACT.md               Contrato estable entre UI y API
docs/WEB_BETA_BRANCHING_GUIDE.md   Ramas y responsabilidades del equipo web
paper/                             Paper en espanol e ingles, figuras y BibTeX
scripts/build_model_artifacts.py   Rebuild de artefactos del modelo
scripts/bootstrap_school_system.py Inicializacion de base de datos y admin
scripts/smoke_test_web_beta.py     Prueba rapida del sistema web
requirements.txt                   Dependencias del proyecto
```

## Notebook

```bash
pip install -r requirements.txt
jupyter notebook Proyecto_GPA.ipynb
```

Tambien puede abrirse en VS Code y ejecutarse con `Run All`.

## Sistema escolar web

```bash
pip install -r requirements.txt
python scripts/build_model_artifacts.py
python scripts/bootstrap_school_system.py
python scripts/smoke_test_web_beta.py
python -m uvicorn web.backend.app:app --reload
```

Abrir en navegador:

```text
http://127.0.0.1:8000
```

Rutas utiles de la demo:

```text
/student/report
/admin/students/{id}/report
/admin/grades/template.csv
```

Credenciales demo:

```text
admin@prepateam.local
Admin1234!
edson@prepateam.mx
prepateam
francisco@prepateam.mx
prepateam
alan@prepateam.mx
prepateam
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

Las recomendaciones son simulaciones del modelo. No se usan `StudentID`, `GradeClass`, `Gender` ni `Ethnicity` para sugerir acciones y la herramienta no debe presentarse como garantia de calificacion ni como sustituto de un tutor o directivo.
