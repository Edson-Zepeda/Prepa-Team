# Frontend beta

La tarea del frontend es hacer una interfaz simple para estudiantes y conectar con el endpoint:

```text
POST http://127.0.0.1:8000/predict
```

Ya existe un archivo inicial:

```text
web/frontend/index.html
```

Puede abrirse directo en el navegador. Si el equipo decide usar React, Vite o Next, este HTML sirve como referencia de campos y respuesta.

## Campos del formulario

Mostrar solo estos campos:

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

No mostrar:

```text
StudentID
GradeClass
Gender
Ethnicity
```

## Ejemplo de llamada

```js
const response = await fetch("http://127.0.0.1:8000/predict", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    Age: 17,
    StudyTimeWeekly: 8,
    Absences: 10,
    ParentalEducation: 2,
    Tutoring: 0,
    ParentalSupport: 2,
    Extracurricular: 0,
    Sports: 1,
    Music: 0,
    Volunteering: 0
  })
});

const result = await response.json();
```

## Que mostrar en pantalla

Mostrar:

- `estimated_gpa`
- `good_performance_probability`
- `risk_level`
- `messages`
- `recommended_plan.plan`
- `recommended_plan.estimated_gpa_after`
- `recommended_plan.probability_after`

## Texto etico visible

```text
Esta herramienta es un simulador academico. No garantiza calificaciones ni sustituye la orientacion de un tutor o docente.
```
