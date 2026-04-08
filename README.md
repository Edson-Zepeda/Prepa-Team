# Proyecto GPA

Proyecto de analisis predictivo para estimar el rendimiento academico de estudiantes y generar recomendaciones accionables de intervencion temprana.

## Objetivo

El proyecto busca:

- Predecir el `GPA` de un estudiante.
- Comparar modelos de regresion: `LinearRegression`, `RandomForest`, `SVR` y `XGBoost`.
- Analizar por que `XGBoost` no supera al modelo lineal.
- Medir el impacto de quitar `Absences`.
- Estimar la probabilidad de buen rendimiento (`GPA >= 2.5`).
- Generar planes de mejora para estudiantes con riesgo academico.
- Documentar el trabajo en formato de paper profesional.

## Archivos principales

```text
Proyecto_GPA.ipynb
data/raw/student_performance.csv
paper/Paper_Proyecto_GPA.md
paper/Paper_Proyecto_GPA.tex
paper/references.bib
paper/generate_paper_assets.py
paper/figures/
paper/tables/
requirements.txt
```

## Como ejecutar el notebook

```bash
pip install -r requirements.txt
jupyter notebook Proyecto_GPA.ipynb
```

En VS Code tambien puede abrirse `Proyecto_GPA.ipynb` y ejecutarse con `Run All`.

## Como regenerar figuras y tablas del paper

```bash
python paper/generate_paper_assets.py
```

Esto actualiza:

```text
paper/figures/
paper/tables/
paper/paper_metrics_summary.json
```

## Como generar el PDF en Overleaf

Esta maquina no tiene `pdflatex` ni `pandoc` instalados, por lo que el PDF se debe compilar en Overleaf.

Pasos:

1. Subir la carpeta `paper/` completa a Overleaf.
2. Abrir `Paper_Proyecto_GPA.tex` como archivo principal.
3. Compilar con BibTeX habilitado para usar `references.bib`.
4. Descargar el PDF generado.

## Nota etica

El motor de recomendaciones no usa `Gender`, `Ethnicity`, `StudentID` ni `GradeClass` para sugerir acciones. Las recomendaciones son simulaciones del modelo y deben usarse como apoyo supervisado, no como decisiones automaticas sobre estudiantes.
