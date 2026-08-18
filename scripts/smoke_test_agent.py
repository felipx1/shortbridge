"""Real end-to-end test of the home-agent flow: a real yt-dlp download
(against a real video from the connected channel) + upload through the
actual FastAPI app (TestClient, real DB, real auth dependency) +
confirms a correctly-linked MediaAsset comes out the other end. Doesn't
run scripts/agent/shortbridge_agent.py itself (that needs a live server
and real network round-trips against an actual deployment -- this proves
the pieces it depends on work correctly)."""
import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.database import engine, init_db
from app.main import app
from app.models import AuditEvent, MediaAsset, YouTubeVideo
from app.providers import youtube_unofficial

REAL_SHORT_VIDEO_ID = "xzv75yDLr3E"
AGENT_TOKEN = "local-dev-test-token-12345"  # matches .env for local dev

init_db()

with Session(engine) as session:
    existing = session.exec(select(YouTubeVideo).where(YouTubeVideo.youtube_video_id == REAL_SHORT_VIDEO_ID)).first()
    if existing:
        for asset in session.exec(select(MediaAsset).where(MediaAsset.youtube_video_id == existing.id)).all():
            for event in session.exec(select(AuditEvent).where(AuditEvent.related_media_asset_id == asset.id)).all():
                session.delete(event)
            session.delete(asset)
        session.delete(existing)
        session.commit()

    video = YouTubeVideo(
        youtube_video_id=REAL_SHORT_VIDEO_ID,
        channel_id="test-channel",
        title="agent smoke test short",
        detected_as_short=True,
        detection_reason="test fixture",
    )
    session.add(video)
    session.commit()
    session.refresh(video)
    video_id = video.id

client = TestClient(app)
client.__enter__()

headers = {"Authorization": f"Bearer {AGENT_TOKEN}"}

# Wrong token -> 401
r = client.get("/api/agent/pending-downloads", headers={"Authorization": "Bearer wrong"})
assert r.status_code == 401, r.status_code
print("Wrong token -> 401  OK")

# No token -> 401
r = client.get("/api/agent/pending-downloads")
assert r.status_code == 401, r.status_code
print("No token -> 401  OK")

# Correct token -> our test video should be in the pending list
r = client.get("/api/agent/pending-downloads", headers=headers, params={"limit": 20})
assert r.status_code == 200, (r.status_code, r.text)
videos = r.json()["videos"]
assert any(v["id"] == video_id for v in videos), f"test video not in pending list: {videos}"
print(f"GET /api/agent/pending-downloads -> 200, test video present ({len(videos)} pending total)  OK")

# Now actually download it (real yt-dlp, real network) and upload it, exactly like the agent script would
tmp_dir = Path(tempfile.mkdtemp(prefix="smoke-agent-"))
try:
    downloaded_path = youtube_unofficial.download_video(REAL_SHORT_VIDEO_ID, tmp_dir)
    print(f"Downloaded {downloaded_path} ({downloaded_path.stat().st_size / 1024:.1f} KB)")

    with open(downloaded_path, "rb") as f:
        r = client.post(
            f"/api/agent/videos/{video_id}/upload",
            headers=headers,
            files={"file": (downloaded_path.name, f, "video/mp4")},
        )
    assert r.status_code == 200, (r.status_code, r.text)
    result = r.json()
    print(f"POST upload -> 200: {result}")
    assert result["width"] == 360 and result["height"] == 640, result
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)

# Video should no longer show up as pending
r = client.get("/api/agent/pending-downloads", headers=headers, params={"limit": 20})
videos = r.json()["videos"]
assert not any(v["id"] == video_id for v in videos), "video still pending after successful upload"
print("Video no longer pending after upload  OK")

with Session(engine) as session:
    asset = session.exec(select(MediaAsset).where(MediaAsset.youtube_video_id == video_id)).one()
    assert asset.source.value == "YOUTUBE_SOURCE"
    assert Path(asset.local_path).exists(), f"final file missing at {asset.local_path}"
    print(f"MediaAsset persisted correctly: {asset.local_path}")

    # Cleanup
    for event in session.exec(select(AuditEvent).where(AuditEvent.related_media_asset_id == asset.id)).all():
        session.delete(event)
    session.delete(asset)
    video = session.get(YouTubeVideo, video_id)
    session.delete(video)
    session.commit()
    Path(asset.local_path).unlink(missing_ok=True)

print("\nAGENT API SMOKE TEST PASSED")
