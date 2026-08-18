"""
APScheduler wiring. Kept as a single BackgroundScheduler living inside the
same process as the web app -- no Celery/Redis, per the "no
over-engineering" principle in the spec. This is safe because ShortBridge
is a single-instance deployment; if it ever needs to run more than one
web replica, this would need to move to a dedicated worker process first.

Phase 1 only registers a heartbeat job (proves the scheduler survives
restarts and shows up in /health). youtube_sync, tiktok_publish and
tiktok_status_poll jobs are added by workers/sync.py and workers/publisher.py
once those providers exist (Phase 2+), guarded by settings.is_*_configured
so an unconfigured provider never gets a job scheduled against it.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings

logger = logging.getLogger("shortbridge.scheduler")

scheduler = BackgroundScheduler(timezone="UTC")
_started = False


def _heartbeat() -> None:
    logger.info("scheduler heartbeat ok")


def start_scheduler() -> None:
    global _started
    if _started:
        return
    scheduler.add_job(
        _heartbeat,
        "interval",
        minutes=30,
        id="heartbeat",
        replace_existing=True,
        misfire_grace_time=300,
    )

    settings = get_settings()
    if settings.is_google_configured:
        from app.workers.sync import register_youtube_sync_job

        register_youtube_sync_job(scheduler)

    scheduler.start()
    _started = True


def shutdown_scheduler() -> None:
    global _started
    if _started:
        scheduler.shutdown(wait=False)
        _started = False


def scheduler_status() -> str:
    return "ok" if _started and scheduler.running else "stopped"
