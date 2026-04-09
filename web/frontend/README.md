# Frontend del sistema escolar

La interfaz ya no es un HTML suelto. Ahora se sirve desde FastAPI con plantillas en:

```text
web/frontend/templates/
web/frontend/static/
```

Pantallas principales:

- `login.html`
- `admin_dashboard.html`
- `admin_students.html`
- `admin_student_detail.html`
- `admin_subjects.html`
- `admin_grades_upload.html`
- `student_dashboard.html`
- `student_profile.html`

La app muestra al alumno:

- promedio escolar real `0–10`
- promedio estimado `0–10`
- probabilidad de buen rendimiento
- nivel de riesgo
- mensajes y plan recomendado

Variables usadas para recomendaciones:

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

Variables que no deben mostrarse ni pedirse:

```text
StudentID
GradeClass
Gender
Ethnicity
```
