from __future__ import annotations

from fastapi import APIRouter, Request
from sqlmodel import select

from app.deps import CurrentUserDep, SessionDep
from app.models import Publication, PublicationStatus
from app.templating import templates

router = APIRouter()


@router.get("/queue")
def queue(request: Request, user: CurrentUserDep, session: SessionDep):
    upcoming = session.exec(
        select(Publication)
        .where(Publication.status.in_([PublicationStatus.scheduled, PublicationStatus.ready]))
        .order_by(Publication.scheduled_at)
        .limit(200)
    ).all()
    return templates.TemplateResponse(request, "queue.html", {"user": user, "upcoming": upcoming})
