from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class PublicationStatus(str, Enum):
    new = "NEW"
    ready = "READY"
    scheduled = "SCHEDULED"
    uploading = "UPLOADING"
    processing = "PROCESSING"
    draft = "DRAFT"
    published = "PUBLISHED"
    failed = "FAILED"
    cancelled = "CANCELLED"


# States a retry/re-send is allowed to touch. Anything past this point means
# TikTok has (or might have) already received the video -- publisher.py must
# query Get Post Status by external_publish_id before ever re-uploading.
RETRYABLE_STATES = {PublicationStatus.new, PublicationStatus.ready, PublicationStatus.failed}


class Publication(SQLModel, table=True):
    """The core idempotency record (section 11). The unique constraint on
    (media_asset_id, oauth_account_id) is the actual duplicate guard: a
    second attempt to send the same asset to the same destination account
    must reuse this row, never insert a new one, no matter how many times
    Docker restarts, the scheduler re-fires, or a button gets double-clicked."""

    __table_args__ = (
        UniqueConstraint("media_asset_id", "oauth_account_id", name="uq_publication_asset_account"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    media_asset_id: int = Field(foreign_key="mediaasset.id", index=True)
    provider: str = Field(index=True)  # "tiktok" today; other providers later
    oauth_account_id: int = Field(foreign_key="oauthaccount.id", index=True)

    status: PublicationStatus = Field(default=PublicationStatus.new, index=True)

    scheduled_at: Optional[datetime] = Field(default=None, index=True)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    external_publish_id: Optional[str] = Field(default=None)  # TikTok publish_id, used to poll status
    external_video_id: Optional[str] = Field(default=None)

    original_title: str = ""
    tiktok_caption: str = ""

    attempt_count: int = Field(default=0)
    next_retry_at: Optional[datetime] = Field(default=None)
    last_error_code: Optional[str] = Field(default=None)
    last_error_message: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
