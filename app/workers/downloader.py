"""
Turns a synced YouTubeVideo into an actual local file: unofficial download
(see app/providers/youtube_unofficial.py -- opt-in, ToS caveat) + sha256 +
ffprobe, producing a MediaAsset row already linked to the source video
(no fuzzy import-matching needed here, unlike media/import -- we know
exactly which YouTubeVideo this came from because we requested it by ID).

Runs two ways:
- `download_one_video`: synchronous, used by the manual "Download" button
  in the Library UI for one specific video, right now.
- `run_pending_downloads`: the paced APScheduler job -- one video per
  tick, so a 253-video backlog trickles in over time instead of bursting
  through YouTube all at once (see config.youtube_download_interval_seconds).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from app.models import MediaAsset, MediaSource, YouTubeVideo
from app.models._util import utcnow
from app.providers import youtube_unofficial
from app.services.audit import log_event
from app.services.media import compute_sha256, probe_video

logger = logging.getLogger("shortbridge.workers.downloader")


def download_one_video(session: Session, video: YouTubeVideo) -> MediaAsset:
    """Raises youtube_unofficial.DownloadFailedError on failure (caller
    records it on the YouTubeVideo row so the retry backoff applies)."""
    settings = get_settings()

    file_path = youtube_unofficial.download_video(video.youtube_video_id, settings.media_youtube_dir)

    sha256 = compute_sha256(file_path)
    existing = session.exec(select(MediaAsset).where(MediaAsset.sha256 == sha256)).first()
    if existing:
        # Same bytes already known (e.g. a re-download after a DB reset) --
        # reuse the row rather than violating the sha256 unique constraint.
        file_path.unlink(missing_ok=True)
        return existing

    probe = probe_video(file_path) or {}

    asset = MediaAsset(
        sha256=sha256,
        filename=file_path.name,
        local_path=str(file_path),
        source=MediaSource.youtube_source,
        youtube_video_id=video.id,
        title=video.title,
        description=video.description,
        match_confirmed=True,
        match_confidence=1.0,
        match_reason="downloaded directly by youtube_video_id -- no matching ambiguity",
        **probe,
    )
    session.add(asset)

    video.download_attempted_at = utcnow()
    video.download_error = None
    session.add(video)
    session.commit()
    session.refresh(asset)

    log_event(
        session,
        "youtube_download_completed",
        f"Downloaded '{video.title}' ({probe.get('width', '?')}x{probe.get('height', '?')}, {probe.get('filesize_bytes', 0) / 1_048_576:.1f} MB)",
        media_asset_id=asset.id,
    )
    return asset


def _next_pending_video(session: Session) -> YouTubeVideo | None:
    settings = get_settings()
    retry_cutoff = utcnow() - timedelta(hours=settings.youtube_download_retry_after_hours)

    already_downloaded = select(MediaAsset.youtube_video_id).where(MediaAsset.youtube_video_id.is_not(None))
    candidates = session.exec(
        select(YouTubeVideo)
        .where(YouTubeVideo.id.not_in(already_downloaded))
        .order_by(YouTubeVideo.published_at)
    ).all()

    for video in candidates:
        if not video.is_short:
            continue
        if video.download_attempted_at and video.download_attempted_at > retry_cutoff:
            continue  # recently failed, still in backoff
        return video
    return None


def run_pending_downloads() -> None:
    settings = get_settings()
    if not settings.enable_youtube_unofficial_download:
        return

    with Session(engine) as session:
        video = _next_pending_video(session)
        if video is None:
            return
        try:
            download_one_video(session, video)
        except youtube_unofficial.DownloadFailedError as exc:
            video.download_attempted_at = utcnow()
            video.download_error = str(exc)[:500]
            session.add(video)
            session.commit()
            log_event(
                session,
                "youtube_download_failed",
                f"Download failed for '{video.title}': {exc}",
                level="warning",
                media_asset_id=None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error downloading video %s", video.id)
            video.download_attempted_at = utcnow()
            video.download_error = f"unexpected error: {exc}"[:500]
            session.add(video)
            session.commit()
            log_event(session, "youtube_download_failed", f"Unexpected error downloading '{video.title}': {exc}", level="error")


def register_downloader_job(scheduler: BackgroundScheduler) -> None:
    settings = get_settings()
    if not settings.enable_youtube_unofficial_download:
        return
    scheduler.add_job(
        run_pending_downloads,
        "interval",
        seconds=settings.youtube_download_interval_seconds,
        id="youtube_downloader",
        replace_existing=True,
        misfire_grace_time=60,
    )
