from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from student_success import StudentSuccessService

app = FastAPI(
    title="Student Success API",
    description="API beta para estimar GPA y generar recomendaciones academicas.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_service() -> StudentSuccessService:
    return StudentSuccessService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/schema")
def schema() -> dict[str, Any]:
    return get_service().schema


@app.post("/predict")
def predict(payload: dict[str, Any]) -> dict[str, Any]:
    return get_service().predict(payload)
