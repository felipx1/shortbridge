"""
File-level media helpers: hashing (for the duplicate guard, section 10-11)
and ffprobe metadata extraction (section 16). Shared by every media
source (unofficial download now; local-file/import-archive matching in
the rest of Phase 3)."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Optional, TypedDict


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


class ProbeResult(TypedDict, total=False):
    duration_seconds: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str
    filesize_bytes: int


def probe_video(path: Path) -> Optional[ProbeResult]:
    """Runs ffprobe (bundled in the image, see Dockerfile) and returns the
    fields MediaAsset cares about. Returns None if ffprobe itself fails
    (corrupt file, not a video, etc.) -- caller logs and moves on rather
    than crashing the whole sync/download over one bad file."""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None

    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})

    result: ProbeResult = {}
    if fmt.get("duration"):
        result["duration_seconds"] = float(fmt["duration"])
    if fmt.get("size"):
        result["filesize_bytes"] = int(fmt["size"])
    if video_stream:
        if video_stream.get("width"):
            result["width"] = int(video_stream["width"])
        if video_stream.get("height"):
            result["height"] = int(video_stream["height"])
        if video_stream.get("codec_name"):
            result["video_codec"] = video_stream["codec_name"]
        rate = video_stream.get("avg_frame_rate", "0/0")
        try:
            num, den = rate.split("/")
            if int(den) > 0:
                result["fps"] = round(int(num) / int(den), 2)
        except (ValueError, ZeroDivisionError):
            pass
    if audio_stream and audio_stream.get("codec_name"):
        result["audio_codec"] = audio_stream["codec_name"]

    return result
