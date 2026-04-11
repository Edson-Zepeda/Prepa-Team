# Frontend Del Sistema Escolar

La interfaz se sirve desde FastAPI con plantillas HTML y estilos propios.

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
- `student_report.html`

La app muestra al alumno:

- promedio escolar real `0-10`
- promedio estimado `0-10`
- probabilidad de buen rendimiento
- riesgo académico
- factores prioritarios
- plan recomendado
- reporte imprimible

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
