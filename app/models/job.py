from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class JobType(str, Enum):
    youtube_sync = "youtube_sync"
    tiktok_publish = "tiktok_publish"
    tiktok_status_poll = "tiktok_status_poll"
    tiktok_sync = "tiktok_sync"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class Job(SQLModel, table=True):
    """A tracked run of a background task (APScheduler-triggered or manual).
    Exists so restarts and retries are observable instead of silent -- the
    Logs screen (section 22) reads this, not raw container logs."""

    id: Optional[int] = Field(default=None, primary_key=True)

    job_type: JobType = Field(index=True)
    status: JobStatus = Field(default=JobStatus.pending, index=True)

    publication_id: Optional[int] = Field(default=None, foreign_key="publication.id", index=True)

    attempt_count: int = Field(default=0)

    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)

    result_summary: str = ""
    error_message: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow)
