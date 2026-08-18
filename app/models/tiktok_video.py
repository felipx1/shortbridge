from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class TikTokVideo(SQLModel, table=True):
    """Videos already on the connected TikTok account, synced via
    video.list when that scope is granted. Second layer of duplicate
    protection per section 19 -- never trust title equality alone; the
    duplicate detector also compares this against MediaAsset.sha256 sent
    history recorded on Publication."""

    id: Optional[int] = Field(default=None, primary_key=True)

    oauth_account_id: int = Field(foreign_key="oauthaccount.id", index=True)
    tiktok_video_id: str = Field(index=True, unique=True)

    title: str = ""
    tiktok_created_at: Optional[datetime] = Field(default=None)
    url: str = ""
    duration_seconds: Optional[float] = Field(default=None)

    last_synced_at: datetime = Field(default_factory=utcnow)
