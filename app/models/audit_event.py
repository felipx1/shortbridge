from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class AuditEvent(SQLModel, table=True):
    """Human-readable event log for the Logs screen (section 22): 'YouTube
    connected', 'Sync found 12 new Shorts', 'Sent Short 042 to TikTok
    (draft)', 'Publication #17 failed: token expired'. Deliberately NOT a
    dump of technical logs -- those stay in `docker compose logs`."""

    id: Optional[int] = Field(default=None, primary_key=True)

    event_type: str = Field(index=True)
    message: str
    level: str = "info"  # info | warning | error

    related_publication_id: Optional[int] = Field(default=None, foreign_key="publication.id")
    related_media_asset_id: Optional[int] = Field(default=None, foreign_key="mediaasset.id")

    created_at: datetime = Field(default_factory=utcnow, index=True)
