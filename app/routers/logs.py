from __future__ import annotations

from fastapi import APIRouter, Request
from sqlmodel import select

from app.deps import CurrentUserDep, SessionDep
from app.models import AuditEvent
from app.templating import templates

router = APIRouter()


@router.get("/logs")
def logs(request: Request, user: CurrentUserDep, session: SessionDep):
    events = session.exec(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(200)).all()
    return templates.TemplateResponse(request, "logs.html", {"user": user, "events": events})
