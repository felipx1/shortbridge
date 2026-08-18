"""Real integration test for the downloader worker's DB-facing logic:
download_one_video() actually creates a correctly-linked MediaAsset, and
_next_pending_video() correctly skips non-Shorts, already-downloaded
videos, and videos still in their failure backoff window. Uses a real
video from the connected channel and the real local SQLite DB (not
mocked) -- see scripts/smoke_test_download.py for the lower-level
download+hash+probe pipeline test."""
from datetime import timedelta

from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine, init_db
from app.models import AuditEvent, MediaAsset, YouTubeVideo
from app.models._util import utcnow
from app.workers.downloader import _next_pending_video, download_one_video


def _delete_asset(session: Session, asset: MediaAsset) -> None:
    for event in session.exec(select(AuditEvent).where(AuditEvent.related_media_asset_id == asset.id)).all():
        session.delete(event)
    session.delete(asset)

REAL_SHORT_VIDEO_ID = "xzv75yDLr3E"  # from the connected channel, confirmed vertical 360x640

init_db()

TEST_FIXTURE_IDS = [REAL_SHORT_VIDEO_ID, "fake-failed-recent", "fake-not-short", "fake-failed-old"]

with Session(engine) as session:
    # Clean slate, in case a previous run of this script left state behind.
    for fixture_id in TEST_FIXTURE_IDS:
        existing_video = session.exec(select(YouTubeVideo).where(YouTubeVideo.youtube_video_id == fixture_id)).first()
        if existing_video:
            for asset in session.exec(select(MediaAsset).where(MediaAsset.youtube_video_id == existing_video.id)).all():
                _delete_asset(session, asset)
            session.delete(existing_video)
    session.commit()

    video = YouTubeVideo(
        youtube_video_id=REAL_SHORT_VIDEO_ID,
        channel_id="test-channel",
        title="smoke test short",
        duration_seconds=4.0,
        detected_as_short=True,
        detection_reason="test fixture",
    )
    session.add(video)
    session.commit()
    session.refresh(video)
    video_id = video.id
    print(f"Created test YouTubeVideo id={video_id}")

    asset = download_one_video(session, video)
    assert asset.id is not None
    assert asset.youtube_video_id == video_id
    assert asset.match_confirmed is True
    assert asset.match_confidence == 1.0
    assert asset.width == 360 and asset.height == 640, (asset.width, asset.height)
    assert asset.duration_seconds and 3 <= asset.duration_seconds <= 6
    assert len(asset.sha256) == 64
    print(f"MediaAsset created: {asset.width}x{asset.height}, {asset.duration_seconds:.1f}s, sha256={asset.sha256[:12]}...")

with Session(engine) as session:
    # _next_pending_video must NOT return this video anymore -- it already has media.
    reloaded_video = session.exec(select(YouTubeVideo).where(YouTubeVideo.youtube_video_id == REAL_SHORT_VIDEO_ID)).one()
    candidates = []
    next_pending = _next_pending_video(session)
    print(f"_next_pending_video after download: {'skipped correctly' if (next_pending is None or next_pending.id != reloaded_video.id) else 'BUG: returned the already-downloaded video'}")
    assert next_pending is None or next_pending.id != reloaded_video.id

    # A failed-recently video must be skipped (backoff), a not-short video must be skipped.
    settings = get_settings()
    failed_video = YouTubeVideo(
        youtube_video_id="fake-failed-recent",
        channel_id="test-channel",
        title="recently failed",
        detected_as_short=True,
        download_attempted_at=utcnow(),
        download_error="simulated failure",
    )
    not_short_video = YouTubeVideo(
        youtube_video_id="fake-not-short",
        channel_id="test-channel",
        title="not a short",
        detected_as_short=False,
    )
    old_failed_video = YouTubeVideo(
        youtube_video_id="fake-failed-old",
        channel_id="test-channel",
        title="failed long ago -- should be retried",
        detected_as_short=True,
        download_attempted_at=utcnow() - timedelta(hours=settings.youtube_download_retry_after_hours + 1),
        download_error="simulated old failure",
    )
    session.add_all([failed_video, not_short_video, old_failed_video])
    session.commit()

    next_pending = _next_pending_video(session)
    assert next_pending is not None, "expected the old-failed video to be eligible for retry"
    assert next_pending.youtube_video_id == "fake-failed-old", next_pending.youtube_video_id
    print(f"_next_pending_video correctly picked the stale-backoff video: {next_pending.youtube_video_id}")

    # Cleanup
    for v in [reloaded_video, failed_video, not_short_video, old_failed_video]:
        v_id = v.id
        for asset in session.exec(select(MediaAsset).where(MediaAsset.youtube_video_id == v_id)).all():
            _delete_asset(session, asset)
        session.delete(v)
    session.commit()

print("\nDOWNLOADER WORKER SMOKE TEST PASSED")
