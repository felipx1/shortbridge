from __future__ import annotations

from fastapi import APIRouter, Request
from sqlmodel import select

from app.deps import CurrentUserDep, SessionDep
from app.models import YouTubeVideo
from app.templating import templates

router = APIRouter()


@router.get("/library")
def library(request: Request, user: CurrentUserDep, session: SessionDep):
    videos = session.exec(
        select(YouTubeVideo).order_by(YouTubeVideo.published_at.desc()).limit(200)
    ).all()
    return templates.TemplateResponse(request, "library.html", {"user": user, "videos": videos})
