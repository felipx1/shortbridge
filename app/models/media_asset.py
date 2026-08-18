from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class MediaSource(str, Enum):
    local_file = "LOCAL_FILE"       # dropped in media/inbox by the user
    import_archive = "IMPORT_ARCHIVE"  # matched from media/import against a YouTubeVideo
    youtube_source = "YOUTUBE_SOURCE"  # obtained via an official YouTube-supported method, if one exists


class MediaAsset(SQLModel, table=True):
    """A single physical video file ShortBridge knows about. See section 10.

    This is deliberately decoupled from YouTubeVideo: a MediaAsset may exist
    with no youtube_video_id (freshly imported, not yet matched), and a
    YouTubeVideo may exist with no MediaAsset (discovered via sync, no local
    file available yet). services.duplicate_detector joins them."""

    id: Optional[int] = Field(default=None, primary_key=True)

    sha256: str = Field(index=True, unique=True)
    filename: str
    local_path: str

    source: MediaSource

    youtube_video_id: Optional[int] = Field(default=None, foreign_key="youtubevideo.id", index=True)

    title: str = ""
    description: str = ""

    duration_seconds: Optional[float] = Field(default=None)
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    fps: Optional[float] = Field(default=None)
    video_codec: Optional[str] = Field(default=None)
    audio_codec: Optional[str] = Field(default=None)
    filesize_bytes: Optional[int] = Field(default=None)

    # Set once ffprobe/ffmpeg has produced a TikTok-compatible copy, kept as
    # a separate file/entity from the original per section 16.
    processed_local_path: Optional[str] = Field(default=None)

    # NULL = not yet reviewed by the matching UI (section 9). True/False =
    # a human or an automatic high-confidence match decided it.
    match_confirmed: Optional[bool] = Field(default=None)
    match_confidence: Optional[float] = Field(default=None)
    match_reason: str = ""

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
