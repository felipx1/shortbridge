"""
Periodic YouTube channel sync (section 7). Stub until Phase 2 implements
app.providers.youtube -- registered as a job only when Google OAuth is
configured (see app.services.scheduler.start_scheduler).
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings

logger = logging.getLogger("shortbridge.workers.sync")


def run_youtube_sync() -> None:
    # Phase 2: iterate connected Google OAuthAccounts, call
    # app.providers.youtube.sync_channel(account), upsert YouTubeVideo rows,
    # log an AuditEvent summarizing new/updated counts.
    logger.info("youtube sync placeholder ran (Phase 2 not implemented yet)")


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
