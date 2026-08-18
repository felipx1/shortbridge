from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.database import engine
from app.services.scheduler import scheduler_status

router = APIRouter()


@router.get("/health")
def health():
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"

    overall = "ok" if db_status == "ok" and scheduler_status() == "ok" else "degraded"
    return {"status": overall, "database": db_status, "scheduler": scheduler_status()}
