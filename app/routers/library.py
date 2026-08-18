from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.config import get_settings
from app.deps import CurrentUserDep, SessionDep
from app.models import MediaAsset, YouTubeVideo
from app.providers.youtube_unofficial import DownloadFailedError
from app.security import create_csrf_token, verify_csrf_token
from app.services.audit import log_event
from app.templating import templates
from app.workers.downloader import download_one_video

router = APIRouter()


@router.get("/library")
def library(request: Request, user: CurrentUserDep, session: SessionDep):
    settings = get_settings()
    filter_ = request.query_params.get("filter", "shorts")
    all_videos = session.exec(select(YouTubeVideo).order_by(YouTubeVideo.published_at.desc()).limit(500)).all()

    if filter_ == "shorts":
        videos = [v for v in all_videos if v.is_short]
    elif filter_ == "not_shorts":
        videos = [v for v in all_videos if not v.is_short]
    else:
        videos = all_videos

    video_ids = [v.id for v in videos]
    assets = session.exec(select(MediaAsset).where(MediaAsset.youtube_video_id.in_(video_ids))).all()
    media_by_video_id = {a.youtube_video_id: a for a in assets}

    return templates.TemplateResponse(
        request,
        "library.html",
        {
            "user": user,
            "videos": videos,
            "filter": filter_,
            "total_synced": len(all_videos),
            "csrf_token": create_csrf_token(),
            "media_by_video_id": media_by_video_id,
            "download_enabled": settings.enable_youtube_unofficial_download,
        },
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


@router.post("/library/{video_id}/download")
def download_now(
    video_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    csrf_token: str = Form(...),
    filter: str = Form("shorts"),
):
    if not verify_csrf_token(csrf_token):
        raise HTTPException(status_code=400, detail="Invalid or expired CSRF token")
    settings = get_settings()
    if not settings.enable_youtube_unofficial_download:
        raise HTTPException(status_code=400, detail="Unofficial download is not enabled")

    video = session.get(YouTubeVideo, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        download_one_video(session, video)
    except DownloadFailedError as exc:
        from app.models._util import utcnow

        video.download_attempted_at = utcnow()
        video.download_error = str(exc)[:500]
        session.add(video)
        session.commit()
        log_event(session, "youtube_download_failed", f"Download failed for '{video.title}': {exc}", level="warning")

    return RedirectResponse(url=f"/library?filter={filter}", status_code=303)
