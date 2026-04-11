from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from student_success import StudentSuccessService
from student_success.config import ADVICE_FEATURES, FIELD_LIMITS

from .db import PROFILE_FIELDS, SchoolRepository
from .settings import get_settings


settings = get_settings()
repository = SchoolRepository(settings)
service = StudentSuccessService()
templates = Jinja2Templates(directory=str(settings.templates_dir))


def percent_display(probability: float | None) -> str:
    if probability is None:
        return "--"
    value = float(probability)
    if value >= 0.995:
        return "99%"
    if value <= 0.005:
        return "<1%"
    return f"{round(value * 100):.0f}%"


def role_label(role: str | None) -> str:
    mapping = {"admin": "Administrador", "student": "Alumno"}
    return mapping.get(role or "", role or "")


def title_case_es(value: Any) -> str:
    if value is None:
        return "--"
    text = str(value).strip()
    return text[:1].upper() + text[1:] if text else "--"


def risk_badge_class(level: str | None) -> str:
    if level == "bajo":
        return "status-ok"
    if level == "medio":
        return "status-warn"
    return "status-danger"


templates.env.filters["percent_display"] = percent_display
templates.env.filters["role_label"] = role_label
templates.env.filters["title_case_es"] = title_case_es
templates.env.filters["risk_badge_class"] = risk_badge_class

app = FastAPI(
    title="Sistema de control escolar",
    description="Sistema de control escolar con planes de intervención mínima para estudiantes y directivos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")


@app.middleware("http")
async def force_connection_close(request: Request, call_next):
    response = await call_next(request)
    response.headers["Connection"] = "close"
    return response


@app.on_event("startup")
def startup() -> None:
    repository.initialize()


def current_user(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(settings.session_cookie_name)
    return repository.get_session_user(token)


def require_user(request: Request, role: str | None = None) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado.")
    if role and user["role"] != role:
        raise HTTPException(status_code=403, detail="Acceso no autorizado.")
    return user


def redirect(url: str, status_code: int = 303) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=status_code)
    response.headers["Connection"] = "close"
    return response


def redirect_with_message(path: str, message: str | None = None, error: str | None = None) -> RedirectResponse:
    pieces = []
    if message:
        pieces.append(f"message={quote(message)}")
    if error:
        pieces.append(f"error={quote(error)}")
    url = path if not pieces else f"{path}?{'&'.join(pieces)}"
    return redirect(url)


def render(request: Request, template_name: str, **context: Any):
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "request": request,
            "current_user": current_user(request),
            "school_name": settings.school_name,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
            **context,
        },
    )


def profile_form_payload(
    age: int,
    study_time_weekly: float,
    absences: int,
    parental_education: int,
    tutoring: int,
    parental_support: int,
    extracurricular: int,
    sports: int,
    music: int,
    volunteering: int,
) -> dict[str, Any]:
    return {
        "Age": age,
        "StudyTimeWeekly": study_time_weekly,
        "Absences": absences,
        "ParentalEducation": parental_education,
        "Tutoring": tutoring,
        "ParentalSupport": parental_support,
        "Extracurricular": extracurricular,
        "Sports": sports,
        "Music": music,
        "Volunteering": volunteering,
    }


def student_prediction(student_id: int) -> dict[str, Any] | None:
    payload = repository.profile_payload(student_id)
    if not payload:
        return None
    return service.predict(payload)


def student_dashboard_context(student_id: int) -> dict[str, Any]:
    student = repository.get_student(student_id)
    profile = repository.get_profile(student_id)
    grades = repository.list_student_grades(student_id)
    school_average = repository.average_for_student(student_id)
    prediction = student_prediction(student_id)
    approved_count = sum(1 for row in grades if row["status"] == "approved")
    failed_count = sum(1 for row in grades if row["status"] == "failed")
    return {
        "student": student,
        "profile": profile,
        "profile_complete": repository.profile_is_complete(student_id),
        "grades": grades,
        "school_average": school_average,
        "approved_count": approved_count,
        "failed_count": failed_count,
        "prediction": prediction,
    }


def report_context(student_id: int) -> dict[str, Any]:
    context = student_dashboard_context(student_id)
    context["generated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return context


def admin_dashboard_context() -> dict[str, Any]:
    students = repository.list_students()
    incomplete_profiles = 0
    at_risk_students = 0
    recent_predictions: list[dict[str, Any]] = []
    for student in students:
        if not repository.profile_is_complete(int(student["id"])):
            incomplete_profiles += 1
            continue
        prediction = student_prediction(int(student["id"]))
        if prediction and prediction["good_performance_probability"] < 0.5:
            at_risk_students += 1
        if prediction:
            recent_predictions.append(
                {
                    "student_id": student["id"],
                    "full_name": student["full_name"],
                    "estimated_average_10": prediction["estimated_average_10"],
                    "risk_level": prediction["risk_level"],
                    "good_performance_probability": prediction["good_performance_probability"],
                }
            )
    counts = repository.student_counts()
    return {
        "students": students[:8],
        "school_average": repository.school_average(),
        "total_students": counts["total_students"],
        "incomplete_profiles": incomplete_profiles,
        "at_risk_students": at_risk_students,
        "recent_predictions": recent_predictions[:8],
    }


def validate_profile_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    for field in ADVICE_FEATURES:
        if field not in payload:
            issues.append({"field": field, "message": "Campo requerido."})
            continue
        try:
            value = float(payload[field])
        except (TypeError, ValueError):
            issues.append({"field": field, "message": "Debe ser numérico."})
            continue
        lower, upper = FIELD_LIMITS[field]
        if value < lower or value > upper:
            issues.append({"field": field, "message": f"Debe estar entre {lower} y {upper}."})
    return issues


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/schema")
def schema() -> dict[str, Any]:
    return service.schema


@app.get("/")
def root(request: Request):
    user = current_user(request)
    if not user:
        return render(request, "login.html")
    return redirect("/admin/dashboard" if user["role"] == "admin" else "/student/dashboard")


@app.get("/login")
def login_page(request: Request):
    if current_user(request):
        return redirect("/")
    return render(request, "login.html")


@app.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    user = repository.authenticate_user(email, password)
    if not user:
        return render(
            request,
            "login.html",
            error="Credenciales inválidas.",
        )
    token = repository.create_session(int(user["id"]))
    response = redirect("/admin/dashboard" if user["role"] == "admin" else "/student/dashboard")
    response.set_cookie(settings.session_cookie_name, token, httponly=True, samesite="lax")
    return response


@app.get("/logout")
def logout_page(request: Request):
    token = request.cookies.get(settings.session_cookie_name)
    repository.delete_session(token)
    response = redirect("/login")
    response.delete_cookie(settings.session_cookie_name)
    return response


@app.post("/api/auth/login")
async def api_login(request: Request):
    payload = await request.json()
    user = repository.authenticate_user(payload.get("email", ""), payload.get("password", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "Credenciales inválidas."}, status_code=401)
    token = repository.create_session(int(user["id"]))
    response = JSONResponse(
        {
            "ok": True,
            "role": user["role"],
            "redirect_to": "/admin/dashboard" if user["role"] == "admin" else "/student/dashboard",
        }
    )
    response.set_cookie(settings.session_cookie_name, token, httponly=True, samesite="lax")
    return response


@app.post("/api/auth/logout")
def api_logout(request: Request):
    token = request.cookies.get(settings.session_cookie_name)
    repository.delete_session(token)
    response = JSONResponse({"ok": True})
    response.delete_cookie(settings.session_cookie_name)
    return response


@app.get("/admin/dashboard")
def admin_dashboard(request: Request):
    require_user(request, "admin")
    return render(request, "admin_dashboard.html", **admin_dashboard_context())


@app.get("/admin/students")
def admin_students(request: Request, search: str = ""):
    require_user(request, "admin")
    return render(request, "admin_students.html", students=repository.list_students(search), search=search)


@app.get("/admin/students/new")
def admin_new_student(request: Request):
    require_user(request, "admin")
    return render(request, "admin_student_form.html", student=None, profile=repository.get_profile(0))


@app.post("/admin/students/new")
def admin_create_student(
    request: Request,
    student_code: str = Form(...),
    full_name: str = Form(...),
    group_name: str = Form(""),
    current_period: str = Form(""),
    account_email: str = Form(""),
    account_password: str = Form(""),
):
    require_user(request, "admin")
    try:
        student_id = repository.create_student(student_code, full_name, group_name, current_period)
        if account_email.strip() and account_password.strip():
            repository.create_or_update_student_user(student_id, account_email, account_password)
        return redirect_with_message(f"/admin/students/{student_id}", "Alumno creado correctamente.")
    except Exception as exc:
        return render(
            request,
            "admin_student_form.html",
            student={
                "student_code": student_code,
                "full_name": full_name,
                "group_name": group_name,
                "current_period": current_period,
            },
            profile=repository.get_profile(0),
            error=str(exc),
        )


@app.get("/admin/students/{student_id}")
def admin_student_detail(request: Request, student_id: int):
    require_user(request, "admin")
    student = repository.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no encontrado.")
    return render(
        request,
        "admin_student_detail.html",
        **student_dashboard_context(student_id),
        subjects=repository.list_subjects(),
        account=repository.get_student_user(student_id),
    )


@app.post("/admin/students/{student_id}/update")
def admin_update_student(
    request: Request,
    student_id: int,
    student_code: str = Form(...),
    full_name: str = Form(...),
    group_name: str = Form(""),
    current_period: str = Form(""),
    is_active: int = Form(1),
):
    require_user(request, "admin")
    repository.update_student(student_id, student_code, full_name, group_name, current_period, bool(is_active))
    return redirect_with_message(f"/admin/students/{student_id}", "Alumno actualizado.")


@app.post("/admin/students/{student_id}/account")
def admin_update_student_account(
    request: Request,
    student_id: int,
    account_email: str = Form(...),
    account_password: str = Form(...),
):
    require_user(request, "admin")
    repository.create_or_update_student_user(student_id, account_email, account_password)
    return redirect_with_message(f"/admin/students/{student_id}", "Cuenta del alumno actualizada.")


@app.post("/admin/students/{student_id}/profile")
def admin_update_student_profile(
    request: Request,
    student_id: int,
    age: int = Form(...),
    study_time_weekly: float = Form(...),
    absences: int = Form(...),
    parental_education: int = Form(...),
    tutoring: int = Form(...),
    parental_support: int = Form(...),
    extracurricular: int = Form(...),
    sports: int = Form(...),
    music: int = Form(...),
    volunteering: int = Form(...),
):
    require_user(request, "admin")
    payload = profile_form_payload(
        age,
        study_time_weekly,
        absences,
        parental_education,
        tutoring,
        parental_support,
        extracurricular,
        sports,
        music,
        volunteering,
    )
    issues = validate_profile_payload(payload)
    if issues:
        return redirect_with_message(f"/admin/students/{student_id}", error=issues[0]["message"])
    repository.upsert_profile(student_id, payload)
    return redirect_with_message(f"/admin/students/{student_id}", "Perfil actualizado.")


@app.post("/admin/students/{student_id}/grade")
def admin_upsert_grade(
    request: Request,
    student_id: int,
    subject_name: str = Form(...),
    period: str = Form(...),
    grade: float = Form(...),
):
    require_user(request, "admin")
    if grade < 0 or grade > 10:
        return redirect_with_message(f"/admin/students/{student_id}", error="La calificación debe estar entre 0 y 10.")
    subject_id = repository.get_or_create_subject(subject_name)
    repository.upsert_grade_record(student_id, subject_id, period, grade, "manual")
    return redirect_with_message(f"/admin/students/{student_id}", "Calificación guardada.")


@app.get("/admin/subjects")
def admin_subjects(request: Request):
    require_user(request, "admin")
    return render(request, "admin_subjects.html", subjects=repository.list_subjects())


@app.post("/admin/subjects")
def admin_create_subject(request: Request, subject_name: str = Form(...)):
    require_user(request, "admin")
    repository.create_subject(subject_name)
    return redirect_with_message("/admin/subjects", "Materia guardada.")


@app.get("/admin/grades/upload")
def admin_grades_upload(request: Request):
    require_user(request, "admin")
    return render(request, "admin_grades_upload.html")


@app.post("/admin/grades/upload")
async def admin_grades_upload_submit(request: Request, csv_file: UploadFile = File(...)):
    user = require_user(request, "admin")
    content = await csv_file.read()
    try:
        summary = repository.import_grades_csv(content, csv_file.filename or "import.csv", int(user["id"]))
        return render(request, "admin_grades_upload.html", import_summary=summary)
    except Exception as exc:
        return render(request, "admin_grades_upload.html", error=str(exc))


@app.get("/admin/grades/template.csv")
def admin_grades_template(request: Request):
    require_user(request, "admin")
    csv_content = "\n".join(
        [
            "student_code,full_name,subject_name,period,grade",
            "PT001,Edson Manuel Zepeda Chavez,Matematicas,2026-A,5.8",
            "PT002,Francisco Ricardo Moreno Sanchez,Programacion,2026-A,9.8",
        ]
    )
    headers = {"Content-Disposition": 'attachment; filename="plantilla_calificaciones.csv"'}
    return Response(content=csv_content, media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/student/dashboard")
def student_dashboard(request: Request):
    user = require_user(request, "student")
    student = repository.get_student_by_user_id(int(user["id"]))
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no asociado a la cuenta.")
    return render(request, "student_dashboard.html", **student_dashboard_context(int(student["id"])))


@app.get("/student/report")
def student_report(request: Request):
    user = require_user(request, "student")
    student = repository.get_student_by_user_id(int(user["id"]))
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no asociado a la cuenta.")
    return render(request, "student_report.html", **report_context(int(student["id"])))


@app.get("/student/profile")
def student_profile(request: Request):
    user = require_user(request, "student")
    student = repository.get_student_by_user_id(int(user["id"]))
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no asociado a la cuenta.")
    return render(request, "student_profile.html", student=student, profile=repository.get_profile(int(student["id"])))


@app.post("/student/profile")
def student_profile_submit(
    request: Request,
    age: int = Form(...),
    study_time_weekly: float = Form(...),
    absences: int = Form(...),
    parental_education: int = Form(...),
    tutoring: int = Form(...),
    parental_support: int = Form(...),
    extracurricular: int = Form(...),
    sports: int = Form(...),
    music: int = Form(...),
    volunteering: int = Form(...),
):
    user = require_user(request, "student")
    student = repository.get_student_by_user_id(int(user["id"]))
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no asociado a la cuenta.")
    payload = profile_form_payload(
        age,
        study_time_weekly,
        absences,
        parental_education,
        tutoring,
        parental_support,
        extracurricular,
        sports,
        music,
        volunteering,
    )
    issues = validate_profile_payload(payload)
    if issues:
        return redirect_with_message("/student/profile", error=issues[0]["message"])
    repository.upsert_profile(int(student["id"]), payload)
    return redirect_with_message("/student/profile", "Perfil actualizado correctamente.")


@app.post("/predict")
async def public_predict(request: Request):
    payload = await request.json()
    return service.predict(payload)


@app.get("/api/student/me")
def api_student_me(request: Request):
    user = require_user(request, "student")
    student = repository.get_student_by_user_id(int(user["id"]))
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no asociado.")
    context = student_dashboard_context(int(student["id"]))
    return {
        "ok": True,
        "student": context["student"],
        "school_average": context["school_average"],
        "approved_count": context["approved_count"],
        "failed_count": context["failed_count"],
        "profile_complete": context["profile_complete"],
        "grades": context["grades"],
        "prediction": context["prediction"],
    }


@app.put("/api/student/profile")
async def api_student_profile(request: Request):
    user = require_user(request, "student")
    student = repository.get_student_by_user_id(int(user["id"]))
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no asociado.")
    payload = await request.json()
    issues = validate_profile_payload(payload)
    if issues:
        return JSONResponse({"ok": False, "errors": issues}, status_code=422)
    repository.upsert_profile(int(student["id"]), payload)
    return {"ok": True}


@app.post("/api/student/predict")
def api_student_predict(request: Request):
    user = require_user(request, "student")
    student = repository.get_student_by_user_id(int(user["id"]))
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no asociado.")
    payload = repository.profile_payload(int(student["id"]))
    if not payload:
        return JSONResponse(
            {
                "ok": False,
                "errors": [{"field": "profile", "message": "El perfil del alumno está incompleto."}],
            },
            status_code=422,
        )
    return service.predict(payload)


@app.get("/api/admin/students/{student_id}/predict")
def api_admin_student_predict(request: Request, student_id: int):
    require_user(request, "admin")
    payload = repository.profile_payload(student_id)
    if not payload:
        return JSONResponse(
            {
                "ok": False,
                "errors": [{"field": "profile", "message": "El perfil del alumno está incompleto."}],
            },
            status_code=422,
        )
    return service.predict(payload)


@app.get("/admin/students/{student_id}/report")
def admin_student_report(request: Request, student_id: int):
    require_user(request, "admin")
    student = repository.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Alumno no encontrado.")
    return render(request, "student_report.html", **report_context(student_id))


@app.post("/api/admin/students")
async def api_admin_create_student(request: Request):
    require_user(request, "admin")
    payload = await request.json()
    try:
        student_id = repository.create_student(
            payload["student_code"],
            payload["full_name"],
            payload.get("group_name", ""),
            payload.get("current_period", ""),
        )
        email = payload.get("account_email", "").strip()
        password = payload.get("account_password", "").strip()
        if email and password:
            repository.create_or_update_student_user(student_id, email, password)
        return {"ok": True, "student_id": student_id}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=422)


@app.post("/api/admin/grades/manual")
async def api_admin_manual_grade(request: Request):
    require_user(request, "admin")
    payload = await request.json()
    grade = float(payload["grade"])
    if grade < 0 or grade > 10:
        return JSONResponse({"ok": False, "error": "La calificación debe estar entre 0 y 10."}, status_code=422)
    subject_id = repository.get_or_create_subject(payload["subject_name"])
    action = repository.upsert_grade_record(
        student_id=int(payload["student_id"]),
        subject_id=subject_id,
        period=payload["period"],
        grade=grade,
        source="manual",
    )
    return {"ok": True, "action": action}


@app.post("/api/admin/grades/import")
async def api_admin_import_grades(request: Request, csv_file: UploadFile = File(...)):
    user = require_user(request, "admin")
    content = await csv_file.read()
    try:
        summary = repository.import_grades_csv(content, csv_file.filename or "import.csv", int(user["id"]))
        return {"ok": True, "summary": summary}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=422)
