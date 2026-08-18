"""
Publishes due Publication rows to TikTok (sections 11, 13, 21). Stub until
Phase 5/6 implement app.providers.tiktok and app.services.duplicate_detector.

The eventual logic, so the shape of things to come is clear:

    due = select Publication where status in (READY, SCHEDULED)
          and scheduled_at <= now and next_retry_at is (null or <= now)
    for each:
        if publication.external_publish_id:
            status = tiktok.get_post_status(publication.external_publish_id)
            reconcile and stop -- never re-upload something TikTok may
            already have received (section 21).
        else:
            upload via tiktok.upload_video(...), store external_publish_id,
            move status to UPLOADING.
    on temporary error (429/5xx/timeout): schedule next_retry_at using
    exponential backoff (1m, 5m, 15m, 1h, capped, configurable max attempts).
"""
from __future__ import annotations

import logging

logger = logging.getLogger("shortbridge.workers.publisher")


def run_due_publications() -> None:
    logger.info("publisher placeholder ran (Phase 5/6 not implemented yet)")
