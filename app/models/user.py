from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class User(SQLModel, table=True):
    """Single admin user for now (see section 23 of the spec). Modeled as a
    real table rather than a hardcoded singleton so multi-user support is a
    schema-compatible addition later, not a migration headache."""

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str  # Argon2id, never the plaintext password
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    last_login_at: Optional[datetime] = Field(default=None)
