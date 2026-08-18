from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.deps import CurrentUserDep, SessionDep
from app.models import YouTubeVideo
from app.security import create_csrf_token, verify_csrf_token
from app.templating import templates

router = APIRouter()


@router.get("/library")
def library(request: Request, user: CurrentUserDep, session: SessionDep):
    filter_ = request.query_params.get("filter", "shorts")
    all_videos = session.exec(select(YouTubeVideo).order_by(YouTubeVideo.published_at.desc()).limit(500)).all()

    if filter_ == "shorts":
        videos = [v for v in all_videos if v.is_short]
    elif filter_ == "not_shorts":
        videos = [v for v in all_videos if not v.is_short]
    else:
        videos = all_videos

    return templates.TemplateResponse(
        request,
        "library.html",
        {"user": user, "videos": videos, "filter": filter_, "total_synced": len(all_videos), "csrf_token": create_csrf_token()},
    )


@router.post("/library/{video_id}/mark-short")
def mark_short(
    video_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    csrf_token: str = Form(...),
    is_short: str = Form(...),
    filter: str = Form("shorts"),
):
    if not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid or expired CSRF token")
    video = session.get(YouTubeVideo, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    video.short_override = is_short == "true"
    session.add(video)
    session.commit()
    return RedirectResponse(url=f"/library?filter={filter}", status_code=303)
