# Guia de ramas para beta web

## Estado del modelo

El modelo ya esta listo como base para la beta web: predice GPA, calcula probabilidad de buen rendimiento (`GPA >= 2.5`) y genera recomendaciones simuladas.

Ya quedo preparado:

- Artefactos del modelo en `models/`.
- Servicio reutilizable en `src/student_success/`.
- API minima en `web/backend/app.py`.
- Frontend HTML inicial en `web/frontend/index.html`.
- Contrato API en `docs/API_CONTRACT.md`.
- Ejemplos en `examples/`.
- Smoke test en `scripts/smoke_test_web_beta.py`.

Lo que todavia falta para la beta:

- Mejorar o reemplazar la interfaz web simple.
- Revisar o adaptar el backend reducido si el equipo quiere cambiar rutas o estilos de respuesta.
- Respetar el contrato estable de entrada y salida.
- Probar frontend y backend juntos.

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

Estas ramas ya estan creadas y subidas en GitHub.

Regla: nadie trabaja directo sobre `main`. Cada quien trabaja en su rama y abre pull request hacia `dev/web-beta`. Cuando la beta compile y funcione, `dev/web-beta` se integra a `main`.

## Responsable 1: Francisco

Rama:

```bash
feature/francisco-student-ui
```

Objetivo:

Crear la interfaz web beta para que el estudiante capture sus datos y vea su resultado. No necesita implementar modelo.

Base ya preparada:

```text
web/frontend/index.html
web/frontend/README.md
docs/API_CONTRACT.md
```

Debe construir:

- Revisar y mejorar la pantalla inicial existente.
- Revisar y mejorar el formulario existente.
- Revisar y mejorar la pantalla de resultados existente.
- Mantener estado de carga y mensaje de error si la API no responde.
- Mejorar diseno responsive si alcanza el tiempo.

No debe pedir en la interfaz:

- `StudentID`
- `GradeClass`
- `Gender`
- `Ethnicity`

Comandos:

```bash
git fetch origin
git checkout feature/francisco-student-ui
git pull origin feature/francisco-student-ui
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

Mantener un backend reducido que reciba los datos del estudiante, llame el servicio del modelo y devuelva mensajes de recomendacion.

Base ya preparada:

```text
web/backend/app.py
src/student_success/
models/
examples/
```

Debe construir:

- Verificar que `GET /health` funcione.
- Verificar que `POST /predict` responda con el JSON esperado.
- Agregar CORS adicional solo si el frontend usa otro puerto.
- Mantener el contrato de `docs/API_CONTRACT.md`.
- Ejecutar `python scripts/smoke_test_web_beta.py` antes de cada PR.

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
  "ok": true,
  "estimated_gpa": 2.2474,
  "good_performance_probability": 0.1502,
  "risk_level": "riesgo alto",
  "messages": [
    "Prioriza reducir ausencias: es el factor con mayor impacto en el modelo.",
    "Aumenta tus horas de estudio semanal de forma sostenida."
  ],
  "recommended_plan": {
    "plan": "reducir ausencias en 10 + aumentar estudio hasta 20h/semana + activar tutoring + aumentar apoyo parental en 2 + activar Extracurricular",
    "estimated_gpa_after": 4.0,
    "probability_after": 1.0,
    "delta_gpa": 1.7526,
    "delta_probability": 0.8498
  }
}
```

Comandos:

```bash
git fetch origin
git checkout feature/alan-model-api
git pull origin feature/alan-model-api
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

El contrato completo esta en:

```text
docs/API_CONTRACT.md
```

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

1. Francisco trabaja en `feature/francisco-student-ui`.
2. Alan trabaja en `feature/alan-model-api`.
3. Ambos mantienen su rama actualizada con `git pull`.
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
