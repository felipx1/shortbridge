"""
ShortBridge home download agent.

Runs on a residential connection (this computer), not the VPS -- because
YouTube's bot detection treats the VPS's datacenter IP far more
aggressively than a residential one (confirmed in production; see
../../UNOFFICIAL_DOWNLOAD.md for the full story). Each run: asks the
server what's still missing, downloads each with yt-dlp (the same code
the server itself uses -- app.providers.youtube_unofficial -- just
running from a different IP), uploads the result, and exits. Meant to be
triggered periodically by Windows Task Scheduler (see
../windows_task_scheduler_setup.ps1), not run as a long-lived process.

Config: copy agent_config.env.example to agent_config.env (gitignored,
holds the agent token -- treat it like a password) in this same
directory, or set SHORTBRIDGE_URL / SHORTBRIDGE_AGENT_TOKEN as real
environment variables.
"""
from __future__ import annotations

import logging
import shutil
import sys
import tempfile
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

    try:
        resp = httpx.get(f"{base_url}/api/agent/pending-downloads", headers=headers, params={"limit": BATCH_SIZE}, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Could not reach ShortBridge: %s", exc)
        return 1

    videos = resp.json().get("videos", [])
    if not videos:
        logger.info("Nothing pending.")
        return 0

    logger.info("%d video(s) pending.", len(videos))
    tmp_dir = Path(tempfile.mkdtemp(prefix="shortbridge-agent-"))
    succeeded = failed = 0
    try:
        for video in videos:
            video_id, yt_id, title = video["id"], video["youtube_video_id"], video["title"]
            logger.info("Downloading %s (%s)...", yt_id, title)
            try:
                file_path = youtube_unofficial.download_video(yt_id, tmp_dir)
            except youtube_unofficial.DownloadFailedError as exc:
                logger.warning("Download failed for %s: %s", yt_id, exc)
                failed += 1
                continue

            try:
                with open(file_path, "rb") as f:
                    upload_resp = httpx.post(
                        f"{base_url}/api/agent/videos/{video_id}/upload",
                        headers=headers,
                        files={"file": (file_path.name, f, "video/mp4")},
                        timeout=180,
                    )
                upload_resp.raise_for_status()
                logger.info("Uploaded %s -> %s", yt_id, upload_resp.json())
                succeeded += 1
            except httpx.HTTPError as exc:
                logger.error("Upload failed for %s: %s", yt_id, exc)
                failed += 1
            finally:
                file_path.unlink(missing_ok=True)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info("Done: %d succeeded, %d failed.", succeeded, failed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
