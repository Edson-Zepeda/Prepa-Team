# Proyecto GPA

Proyecto de analisis y modelado para estimar el rendimiento academico de estudiantes y generar recomendaciones accionables.

## Objetivo

El notebook busca:

- Predecir el `GPA` de un estudiante.
- Comparar modelos de regresion.
- Analizar el comportamiento de `XGBoost`.
- Probar el impacto de quitar `Absences`.
- Estimar la probabilidad de buen rendimiento (`GPA >= 2.5`).
- Generar planes de mejora para estudiantes con riesgo academico.

## Archivos

```text
Proyecto_GPA.ipynb
data/raw/student_performance.csv
requirements.txt
```

## Como ejecutarlo

```bash
pip install -r requirements.txt
jupyter notebook Proyecto_GPA.ipynb
```

En VS Code tambien puede abrirse el notebook y ejecutarse con `Run All`.

## Nota

El motor de recomendaciones evita usar variables sensibles o no accionables como `Gender`, `Ethnicity`, `StudentID` y `GradeClass` para sugerir acciones. Las recomendaciones son simulaciones del modelo y deben usarse como apoyo, no como decision automatica.

