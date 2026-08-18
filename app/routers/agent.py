"""
API for the home download agent (scripts/agent/shortbridge_agent.py) --
NOT the admin web UI. Authenticated with a bearer token
(settings.agent_api_token), not the session cookie: this is a
machine-to-machine client, not a browser.

Exists because YouTube's bot detection treats this VPS's datacenter IP
far more aggressively than a residential one (confirmed in production --
see UNOFFICIAL_DOWNLOAD.md). The agent runs on a residential connection,
downloads with yt-dlp there (where it actually works), and uploads the
finished file here.
"""
from __future__ import annotations

import hashlib
import secrets
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, status

from app.config import get_settings
from app.deps import SessionDep
from app.models import YouTubeVideo
from app.workers.downloader import finalize_downloaded_file, get_pending_videos

router = APIRouter(prefix="/api/agent")


def verify_agent(authorization: Annotated[str | None, Header()] = None) -> None:
    settings = get_settings()
    if not settings.is_agent_configured:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent API is not configured")
    expected = f"Bearer {settings.agent_api_token}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing agent token")


AgentAuthDep = Annotated[None, Depends(verify_agent)]


@router.get("/pending-downloads")
def pending_downloads(session: SessionDep, _: AgentAuthDep, limit: int = 5):
    videos = get_pending_videos(session, limit=limit)
    return {
        "videos": [
            {"id": v.id, "youtube_video_id": v.youtube_video_id, "title": v.title}
            for v in videos
        ]
    }


@router.post("/videos/{video_id}/upload")
async def upload_video(video_id: int, session: SessionDep, _: AgentAuthDep, file: UploadFile):
    video = session.get(YouTubeVideo, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    settings = get_settings()
    tmp_dir = Path(tempfile.mkdtemp(prefix="shortbridge-upload-", dir=settings.media_dir))
    tmp_path = tmp_dir / f"{video.youtube_video_id}.mp4"

    hasher = hashlib.sha256()
    with open(tmp_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            hasher.update(chunk)
            f.write(chunk)

    asset = finalize_downloaded_file(session, video, tmp_path)
    tmp_dir.rmdir()  # file itself was moved by finalize_downloaded_file; dir should be empty now

    return {"media_asset_id": asset.id, "sha256": asset.sha256, "width": asset.width, "height": asset.height}
