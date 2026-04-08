# Guia de ramas para beta web

## Estado del modelo

El modelo ya esta listo como prototipo de investigacion: predice GPA, calcula probabilidad de buen rendimiento (`GPA >= 2.5`) y genera recomendaciones simuladas.

Para usarlo en una web beta todavia falta convertirlo en producto:

- Exportar el pipeline entrenado y el clasificador calibrado como artefactos reutilizables.
- Separar el codigo del notebook en modulos o API.
- Definir un contrato estable de entrada y salida.
- Validar campos antes de predecir.
- Mostrar mensajes de mejora sin usar variables sensibles.
- Agregar pruebas basicas para evitar que la web muestre resultados rotos.

La beta no debe decir que garantiza una calificacion. Debe presentarse como simulador de apoyo academico.

## Ramas del equipo

Rama estable:

```bash
main
```

Rama de integracion para la beta:

```bash
dev/web-beta
```

Ramas de trabajo:

```bash
feature/francisco-student-ui
feature/alan-model-api
```

Regla: nadie trabaja directo sobre `main`. Cada quien trabaja en su rama y abre pull request hacia `dev/web-beta`. Cuando la beta compile y funcione, `dev/web-beta` se integra a `main`.

## Responsable 1: Francisco

Rama:

```bash
feature/francisco-student-ui
```

Objetivo:

Crear la interfaz web beta para que el estudiante capture sus datos y vea su resultado.

Debe construir:

- Pantalla de inicio con explicacion breve del proyecto.
- Formulario de estudiante con campos: `Age`, `StudyTimeWeekly`, `Absences`, `ParentalEducation`, `Tutoring`, `ParentalSupport`, `Extracurricular`, `Sports`, `Music`, `Volunteering`.
- Pantalla de resultados con `GPA estimado`, `probabilidad de buen rendimiento`, `nivel de riesgo` y mensajes de mejora.
- Estado de carga y mensaje de error si la API no responde.
- Diseno responsive para laptop y celular.

No debe pedir en la interfaz:

- `StudentID`
- `GradeClass`
- `Gender`
- `Ethnicity`

Comandos:

```bash
git checkout dev/web-beta
git pull origin dev/web-beta
git checkout -b feature/francisco-student-ui
```

Cuando tenga avance:

```bash
git add .
git commit -m "Add student beta UI"
git push -u origin feature/francisco-student-ui
```

Luego abre pull request hacia:

```bash
dev/web-beta
```

## Responsable 2: Alan

Rama:

```bash
feature/alan-model-api
```

Objetivo:

Crear el servicio que reciba los datos del estudiante, ejecute el modelo y devuelva mensajes de recomendacion.

Debe construir:

- Endpoint de prediccion para un estudiante.
- Validacion de entrada.
- Carga del modelo o entrenamiento temporal desde el dataset para la beta.
- Respuesta JSON con prediccion, probabilidad, nivel de riesgo y recomendaciones.
- Endpoint de salud para saber si la API esta activa.
- Pruebas basicas con uno o dos casos demo.

Entrada esperada:

```json
{
  "Age": 17,
  "StudyTimeWeekly": 8,
  "Absences": 10,
  "ParentalEducation": 2,
  "Tutoring": 0,
  "ParentalSupport": 2,
  "Extracurricular": 0,
  "Sports": 1,
  "Music": 0,
  "Volunteering": 0
}
```

Salida esperada:

```json
{
  "estimated_gpa": 2.31,
  "good_performance_probability": 0.64,
  "risk_level": "riesgo moderado",
  "messages": [
    "Reduce ausencias para mejorar tu rendimiento estimado.",
    "Aumentar horas de estudio puede elevar tu probabilidad de buen rendimiento.",
    "Activar tutoring puede apoyar la mejora academica."
  ],
  "recommended_plan": {
    "plan": "reducir ausencias + aumentar estudio + activar tutoring",
    "estimated_gpa_after": 2.85,
    "probability_after": 0.81,
    "delta_gpa": 0.54,
    "delta_probability": 0.17
  }
}
```

Comandos:

```bash
git checkout dev/web-beta
git pull origin dev/web-beta
git checkout -b feature/alan-model-api
```

Cuando tenga avance:

```bash
git add .
git commit -m "Add model recommendation API"
git push -u origin feature/alan-model-api
```

Luego abre pull request hacia:

```bash
dev/web-beta
```

## Contrato entre UI y API

La UI debe enviar exactamente estos campos:

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

La API debe devolver como minimo:

```text
estimated_gpa
good_performance_probability
risk_level
messages
recommended_plan
```

Reglas:

- `estimated_gpa` debe estar entre `0` y `4`.
- `good_performance_probability` debe estar entre `0` y `1`.
- Los mensajes deben ser claros y accionables.
- No se deben usar variables sensibles para recomendaciones.
- Si falta un campo, la API debe responder error claro y la UI debe mostrarlo.

## Flujo de trabajo recomendado

1. Edson crea o actualiza `dev/web-beta`.
2. Francisco crea `feature/francisco-student-ui` desde `dev/web-beta`.
3. Alan crea `feature/alan-model-api` desde `dev/web-beta`.
4. Cada quien hace commits pequenos y descriptivos.
5. Cada quien abre pull request hacia `dev/web-beta`.
6. Se prueba la beta completa desde `dev/web-beta`.
7. Cuando funcione, se abre pull request de `dev/web-beta` hacia `main`.

## Definicion de beta lista

La beta se considera lista cuando:

- El estudiante puede capturar sus datos desde la web.
- La web muestra GPA estimado.
- La web muestra probabilidad de buen rendimiento.
- La web muestra mensajes de mejora.
- No aparecen `Gender`, `Ethnicity`, `StudentID` ni `GradeClass` en el formulario.
- La API responde con JSON estable.
- Hay al menos dos casos demo probados.
- El README explica como correr frontend y backend.
