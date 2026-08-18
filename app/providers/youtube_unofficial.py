"""
UNOFFICIAL YouTube video download, via yt-dlp. Opt-in only
(ENABLE_YOUTUBE_UNOFFICIAL_DOWNLOAD=true) -- see UNOFFICIAL_DOWNLOAD.md.

This is a deliberate, explicit exception carved out of section 38's "no
scraping / no reverse-engineered endpoints" rule, made with the user's
informed consent after being told plainly: this is not Google's API, it
extracts video streams from YouTube's internal player responses the same
way yt-dlp/youtube-dl always have, it's against YouTube's Terms of
Service, and YouTube changing its internals can break it with no warning.
It exists ONLY because the official Data API has no download capability
for any channel, including your own (verified against current docs, not
assumed) -- there is no compliant automated alternative, only manual ones
(Google Takeout, YouTube Studio's per-video Download button).

Everything else in this codebase (app/providers/youtube.py) talks to
Google's real, documented, ToS-compliant API. Keep it that way -- this
file is intentionally the only place that doesn't, so the boundary stays
obvious and auditable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yt_dlp


class DownloadFailedError(Exception):
    pass


def download_video(youtube_video_id: str, dest_dir: Path, cookie_file: Optional[Path] = None) -> Path:
    """Downloads the given video to dest_dir as "<video_id>.mp4" (merging
    separate video/audio streams via ffmpeg, already in the image from
    Phase 1). Raises DownloadFailedError with yt-dlp's message on failure
    (private, deleted, age-restricted, region-locked, geo-blocked, yt-dlp
    itself out of date against a YouTube change, an expired cookie_file,
    etc.) -- callers decide whether/when to retry, this function doesn't.

    cookie_file (Netscape format -- see scripts/convert_cookies.py) proves
    a real authenticated session to YouTube, which matters most from a
    datacenter IP: those get bot-checked much harder than a residential
    one, and the plain client-spoofing trick below isn't always enough on
    its own from a VPS (confirmed hitting that wall in production)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(dest_dir / f"{youtube_video_id}.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 2,
        "socket_timeout": 30,
        # Without this, YouTube's web client path currently demands
        # "Sign in to confirm you're not a bot" even for a plain public
        # video -- confirmed hitting that wall during development. The
        # android client spoof is a known, commonly-used yt-dlp workaround,
        # not something invented here, but it's exactly the kind of thing
        # that stops working whenever YouTube tightens that client too --
        # if downloads start failing with a bot-check error, that's the
        # first thing to suspect (check for a yt-dlp update; cookie_file
        # above is the other lever).
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }
    if cookie_file is not None:
        ydl_opts["cookiefile"] = str(cookie_file)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={youtube_video_id}"])
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadFailedError(str(exc)) from exc

    result_path = dest_dir / f"{youtube_video_id}.mp4"
    if not result_path.exists():
        raise DownloadFailedError(f"yt-dlp reported success but {result_path} doesn't exist")
    return result_path
