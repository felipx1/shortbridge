"""Real integration test for the unofficial download pipeline -- actually
downloads a video (not mocked), computes its sha256, and runs ffprobe on
it. Uses "Me at the zoo" (jNQXAC9IVRw), the first video ever uploaded to
YouTube -- 19 seconds, about as stable/unlikely-to-disappear a test
fixture as exists on the platform. NOT run as part of CI/automated
suites; run manually to confirm yt-dlp still works against YouTube's
current internals (see UNOFFICIAL_DOWNLOAD.md -- this is expected to need
occasional attention)."""
import shutil
import tempfile
from pathlib import Path

from app.providers import youtube_unofficial
from app.services.media import compute_sha256, probe_video

TEST_VIDEO_ID = "jNQXAC9IVRw"

tmp_dir = Path(tempfile.mkdtemp(prefix="shortbridge-dl-test-"))
try:
    print(f"Downloading {TEST_VIDEO_ID} to {tmp_dir} ...")
    path = youtube_unofficial.download_video(TEST_VIDEO_ID, tmp_dir)
    assert path.exists(), "download reported success but file is missing"
    print(f"Downloaded: {path} ({path.stat().st_size / 1024:.1f} KB)")

    sha = compute_sha256(path)
    assert len(sha) == 64
    print(f"sha256: {sha}")

    probe = probe_video(path)
    assert probe is not None, "ffprobe failed on the downloaded file"
    print(f"ffprobe: {probe}")
    assert probe.get("duration_seconds"), "expected a duration"
    assert 15 <= probe["duration_seconds"] <= 25, f"expected ~19s, got {probe['duration_seconds']}"
    assert probe.get("width") and probe.get("height"), "expected real pixel dimensions"

    print("\nDOWNLOAD PIPELINE SMOKE TEST PASSED")
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
