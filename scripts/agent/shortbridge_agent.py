"""
ShortBridge home download agent -- LOCAL-ONLY MODE.

Runs on a residential connection (this computer), not the VPS -- because
YouTube's bot detection treats the VPS's datacenter IP far more
aggressively than a residential one (confirmed in production; see
../../UNOFFICIAL_DOWNLOAD.md for the full story).

At the user's request, this does NOT upload anything to the server --
it only downloads each Short to LOCAL_ARCHIVE_DIR on this machine and
tracks progress in a local manifest file (.manifest.txt in that folder),
entirely independent of server state. The server's Library page will
keep showing these as not-yet-downloaded; that's expected in this mode.
(Uploading is still possible -- see upload_one_video() below, unused by
main() right now -- if a future need calls for pushing files to the
server instead of/in addition to keeping them here.)

Each run handles up to BATCH_SIZE videos with a short pause between each
(not just between runs) and exits. Run it again for the next batch --
there's no need to wait for one run to "finish the backlog."

Config: copy agent_config.env.example to agent_config.env (gitignored,
holds the agent token -- treat it like a password) in this same
directory, or set SHORTBRIDGE_URL / SHORTBRIDGE_AGENT_TOKEN as real
environment variables.
"""
from __future__ import annotations

import logging
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

import httpx

# Repo root, so `app.providers.youtube_unofficial` is importable without
# installing this project as a package.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.providers import youtube_unofficial  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("shortbridge-agent")

BATCH_SIZE = 5  # videos per run -- keep runs short, run again for more
PAUSE_BETWEEN_VIDEOS_SECONDS = 3  # small gap inside a batch, not just between runs

# Every successfully downloaded video lands here. Gitignored, not part of
# the repo -- just a local archive on this machine.
LOCAL_ARCHIVE_DIR = REPO_ROOT / "downloaded_shorts"
MANIFEST_PATH = LOCAL_ARCHIVE_DIR / ".manifest.txt"


def _safe_filename(title: str, yt_id: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", title).strip()[:80]
    return f"{cleaned} [{yt_id}].mp4" if cleaned else f"{yt_id}.mp4"


def _load_manifest() -> set[str]:
    if not MANIFEST_PATH.exists():
        return set()
    return {line.strip() for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}


def _append_manifest(yt_id: str) -> None:
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(yt_id + "\n")


def _load_config() -> dict[str, str]:
    config: dict[str, str] = {}
    config_file = Path(__file__).parent / "agent_config.env"
    if config_file.exists():
        # utf-8-sig eats a leading BOM if the file gets re-saved by
        # PowerShell's Out-File (adds one by default) -- plain utf-8 would
        # silently glue it onto the first key, breaking the lookup below.
        for line in config_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()

    import os

    config["SHORTBRIDGE_URL"] = os.environ.get("SHORTBRIDGE_URL", config.get("SHORTBRIDGE_URL", ""))
    config["SHORTBRIDGE_AGENT_TOKEN"] = os.environ.get("SHORTBRIDGE_AGENT_TOKEN", config.get("SHORTBRIDGE_AGENT_TOKEN", ""))
    return config


def main() -> int:
    config = _load_config()
    base_url = config["SHORTBRIDGE_URL"].rstrip("/")
    token = config["SHORTBRIDGE_AGENT_TOKEN"]
    if not base_url or not token:
        logger.error("Missing SHORTBRIDGE_URL or SHORTBRIDGE_AGENT_TOKEN -- see agent_config.env.example")
        return 1

    headers = {"Authorization": f"Bearer {token}"}
    LOCAL_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    already_have = _load_manifest()

    try:
        resp = httpx.get(f"{base_url}/api/agent/shorts", headers=headers, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Could not reach ShortBridge: %s", exc)
        return 1

    all_shorts = resp.json().get("videos", [])
    pending = [v for v in all_shorts if v["youtube_video_id"] not in already_have][:BATCH_SIZE]

    if not pending:
        logger.info("Nothing pending (%d already downloaded of %d total Shorts).", len(already_have), len(all_shorts))
        return 0

    logger.info("%d video(s) this run (%d/%d already downloaded).", len(pending), len(already_have), len(all_shorts))
    tmp_dir = Path(tempfile.mkdtemp(prefix="shortbridge-agent-"))
    succeeded = failed = 0
    total_bytes = 0
    try:
        for i, video in enumerate(pending):
            yt_id, title = video["youtube_video_id"], video["title"]
            logger.info("Downloading %s (%s)...", yt_id, title)
            try:
                file_path = youtube_unofficial.download_video(yt_id, tmp_dir)
            except youtube_unofficial.DownloadFailedError as exc:
                logger.warning("Download failed for %s: %s", yt_id, exc)
                failed += 1
                if i < len(pending) - 1:
                    time.sleep(PAUSE_BETWEEN_VIDEOS_SECONDS)
                continue

            archive_path = LOCAL_ARCHIVE_DIR / _safe_filename(title, yt_id)
            shutil.move(str(file_path), str(archive_path))
            size = archive_path.stat().st_size
            total_bytes += size
            _append_manifest(yt_id)
            logger.info("Saved: %s (%.1f MB)", archive_path.name, size / 1_048_576)
            succeeded += 1

            if i < len(pending) - 1:
                time.sleep(PAUSE_BETWEEN_VIDEOS_SECONDS)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info(
        "Done: %d succeeded (%.1f MB, kept in %s), %d failed.",
        succeeded, total_bytes / 1_048_576, LOCAL_ARCHIVE_DIR, failed,
    )
    return 0


def upload_one_video(base_url: str, headers: dict, video_id: int, file_path: Path) -> dict:
    """Not used by main() in local-only mode -- kept for when a future
    workflow needs to push an already-downloaded local file to the
    server instead."""
    with open(file_path, "rb") as f:
        resp = httpx.post(
            f"{base_url}/api/agent/videos/{video_id}/upload",
            headers=headers,
            files={"file": (file_path.name, f, "video/mp4")},
            timeout=180,
        )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    raise SystemExit(main())
