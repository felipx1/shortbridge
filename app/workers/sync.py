"""
YouTube channel sync (section 7): pages through the authenticated channel's
uploads playlist, fetches full video metadata in batches of 50, and
upserts YouTubeVideo rows. Runs both as an APScheduler job (all connected
accounts, every `youtube_sync_interval_hours`) and on-demand from the
Connections page's "Sync now" button (one account, synchronously).
"""
from __future__ import annotations

import logging

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from app.models import OAuthAccount, OAuthProvider, YouTubeVideo
from app.models._util import utcnow
from app.providers import youtube
from app.services.audit import log_event
from app.services.oauth import ReconnectNeededError, get_valid_access_token

logger = logging.getLogger("shortbridge.workers.sync")


def sync_youtube_account(session: Session, account: OAuthAccount) -> dict:
    """Returns {"new": int, "updated": int, "total_seen": int}. Raises
    ReconnectNeededError (already logged by services.oauth) if the token
    can't be refreshed."""
    access_token = get_valid_access_token(session, account)

    channel = youtube.get_own_channel(access_token)
    if channel is None:
        log_event(session, "youtube_sync_failed", f"Could not read channel for account #{account.id}", level="error")
        return {"new": 0, "updated": 0, "total_seen": 0}

    channel_id = channel["id"]
    channel_title = channel.get("snippet", {}).get("title", channel_id)
    if account.display_name != channel_title or account.external_account_id != channel_id:
        account.display_name = channel_title
        account.external_account_id = channel_id
        account.updated_at = utcnow()
        session.add(account)
        session.commit()

    uploads_playlist_id = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads_playlist_id:
        log_event(session, "youtube_sync_failed", f"Channel '{channel_title}' has no uploads playlist", level="error")
        return {"new": 0, "updated": 0, "total_seen": 0}

    new_count = 0
    updated_count = 0
    total_seen = 0
    page_token = None

    while True:
        try:
            page = youtube.list_uploads_page(access_token, uploads_playlist_id, page_token)
        except httpx.HTTPStatusError as exc:
            _log_api_error(session, account, "playlistItems.list", exc)
            break

        video_ids = [
            item["contentDetails"]["videoId"]
            for item in page.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        ]
        total_seen += len(video_ids)

        if video_ids:
            try:
                videos = youtube.get_videos(access_token, video_ids)
            except httpx.HTTPStatusError as exc:
                _log_api_error(session, account, "videos.list", exc)
                break

            for video in videos:
                if _upsert_video(session, video, channel_id):
                    new_count += 1
                else:
                    updated_count += 1
            session.commit()

        page_token = page.get("nextPageToken")
        if not page_token:
            break

    log_event(
        session,
        "youtube_sync_completed",
        f"YouTube sync for '{channel_title}': {new_count} new, {updated_count} updated, {total_seen} videos seen",
    )
    return {"new": new_count, "updated": updated_count, "total_seen": total_seen}


def _upsert_video(session: Session, video: dict, channel_id: str) -> bool:
    """Returns True if a new row was inserted, False if an existing one was updated."""
    video_id = video["id"]
    snippet = video.get("snippet", {})
    content_details = video.get("contentDetails", {})
    status = video.get("status", {})

    duration = youtube.parse_iso8601_duration(content_details.get("duration", ""))
    is_short, reason = youtube.detect_short(video)
    thumb = snippet.get("thumbnails", {}).get("high") or snippet.get("thumbnails", {}).get("default") or {}

    existing = session.exec(select(YouTubeVideo).where(YouTubeVideo.youtube_video_id == video_id)).first()
    row = existing or YouTubeVideo(youtube_video_id=video_id, channel_id=channel_id, title=snippet.get("title", ""))

    row.channel_id = channel_id
    row.title = snippet.get("title", "")
    row.description = snippet.get("description", "")
    row.published_at = youtube.parse_iso8601_datetime(snippet.get("publishedAt", ""))
    row.duration_seconds = duration
    row.thumbnail_url = thumb.get("url", "")
    row.youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    row.privacy_status = status.get("privacyStatus", "")
    row.detected_as_short = is_short
    row.detection_reason = reason
    row.last_synced_at = utcnow()

    session.add(row)
    return existing is None


def _log_api_error(session: Session, account: OAuthAccount, call: str, exc: httpx.HTTPStatusError) -> None:
    status_code = exc.response.status_code
    # 403 quotaExceeded and 429 are the two rate-limit shapes the YouTube
    # Data API uses (section 33) -- both just mean "stop for now", not
    # "something is broken."
    level = "warning" if status_code in (403, 429) else "error"
    log_event(
        session,
        "youtube_sync_failed",
        f"{call} failed for account '{account.display_name}': HTTP {status_code} {exc.response.text[:300]}",
        level=level,
    )


def run_youtube_sync() -> None:
    """APScheduler entrypoint: sync every active, connected Google account."""
    with Session(engine) as session:
        accounts = session.exec(
            select(OAuthAccount).where(OAuthAccount.provider == OAuthProvider.google, OAuthAccount.is_active == True)  # noqa: E712
        ).all()
        if not accounts:
            return
        for account in accounts:
            try:
                sync_youtube_account(session, account)
            except ReconnectNeededError:
                continue  # services.oauth already logged this
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected error syncing account %s", account.id)
                log_event(session, "youtube_sync_failed", f"Unexpected error syncing '{account.display_name}': {exc}", level="error")


def register_youtube_sync_job(scheduler: BackgroundScheduler) -> None:
    settings = get_settings()
    scheduler.add_job(
        run_youtube_sync,
        "interval",
        hours=settings.youtube_sync_interval_hours,
        id="youtube_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )
