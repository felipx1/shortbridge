from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models._util import utcnow


class OAuthProvider(str, Enum):
    google = "google"
    tiktok = "tiktok"


class OAuthAccount(SQLModel, table=True):
    """One connected external account (a YouTube channel via Google, or a
    TikTok account). Tokens are stored encrypted (Fernet, app.services.crypto)
    -- this table must never be dumped/logged raw. See section 24."""

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: OAuthProvider = Field(index=True)

    # Provider-side identifiers, e.g. YouTube channel_id or TikTok open_id.
    external_account_id: str = Field(index=True)
    display_name: str = ""

    # Encrypted at rest. Never serialized to the frontend, never logged.
    encrypted_access_token: Optional[str] = Field(default=None)
    encrypted_refresh_token: Optional[str] = Field(default=None)
    access_token_expires_at: Optional[datetime] = Field(default=None)

    # Space-separated OAuth scopes actually granted (not just requested --
    # TikTok in particular may approve a subset). See sections 12 and 15.
    granted_scopes: str = ""

    is_active: bool = Field(default=True)
    connected_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    disconnected_at: Optional[datetime] = Field(default=None)

    def has_scope(self, scope: str) -> bool:
        return scope in self.granted_scopes.split()
