"""
Shared shape for destination/source providers. YouTube and TikTok
implement this independently -- routers and workers never import a
provider's SDK directly, only this interface -- so adding Instagram/Facebook
later (section 1, 37) means writing a new provider module, not touching the
scheduler, the duplicate detector, or the UI.
"""
from __future__ import annotations

from typing import Protocol

from app.models import OAuthAccount


class ProviderInvalidGrantError(Exception):
    """Base class for 'this refresh token is dead' across providers --
    each provider's own InvalidGrantError inherits from this so
    app.services.oauth can catch one type regardless of which provider
    raised it (revoked, or Google's 7-day Testing-mode expiry, or
    whatever TikTok's equivalent turns out to be)."""


class OAuthProviderClient(Protocol):
    """Common OAuth lifecycle every provider (Google, TikTok, ...) implements."""

    def build_authorize_url(self, state: str) -> str: ...

    def exchange_code_for_tokens(self, code: str) -> dict: ...

    def refresh_access_token(self, account: OAuthAccount) -> dict: ...

    def revoke(self, account: OAuthAccount) -> None: ...
