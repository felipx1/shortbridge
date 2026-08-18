from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class YouTubeVideo(SQLModel, table=True):
    """One video from the synced channel, per section 7. `detected_as_short`
    is a machine guess (section 8); `short_override` lets the user correct it
    from the Library UI without losing the original detection reasoning."""

    id: Optional[int] = Field(default=None, primary_key=True)

    youtube_video_id: str = Field(index=True, unique=True)
    channel_id: str = Field(index=True)

    title: str
    description: str = ""
    published_at: Optional[datetime] = Field(default=None)

    duration_seconds: Optional[float] = Field(default=None)
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)

    thumbnail_url: str = ""
    youtube_url: str = ""
    privacy_status: str = ""

    detected_as_short: bool = Field(default=False)
    detection_reason: str = ""
    # Manual correction from the UI ("Mark as Short" / "Not a Short").
    # None = trust detected_as_short. True/False = human override wins.
    short_override: Optional[bool] = Field(default=None)

    last_synced_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)

    # Unofficial download (yt-dlp, opt-in -- see UNOFFICIAL_DOWNLOAD.md).
    # Time-based backoff on failure (skip retrying for a while) instead of
    # a hot loop hammering a video that's private/deleted/age-restricted.
    download_attempted_at: Optional[datetime] = Field(default=None)
    download_error: Optional[str] = Field(default=None)

    @property
    def is_short(self) -> bool:
        return self.short_override if self.short_override is not None else self.detected_as_short
