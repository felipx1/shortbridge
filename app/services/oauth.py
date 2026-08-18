"""
Provider-agnostic token lifecycle glue: given an OAuthAccount row, get a
currently-valid access token, refreshing it (and persisting the refresh)
if it's expired or about to be. Routers and workers call this instead of
touching encrypted tokens or provider refresh endpoints directly.
"""
from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session

from app.models._util import utcnow
from app.models.oauth_account import OAuthAccount
from app.providers import youtube
from app.providers.youtube import InvalidGrantError
from app.services.audit import log_event
from app.services.crypto import decrypt_token, encrypt_token

# Refresh a bit before actual expiry so a slow request never straddles the
# boundary and gets a 401 mid-call.
_EXPIRY_SAFETY_MARGIN = timedelta(minutes=5)


class ReconnectNeededError(Exception):
    """Raised when the stored refresh token is dead. The account has
    already been flagged (needs_reconnect=True) and an AuditEvent logged;
    this just stops the caller from proceeding as if it had a token."""


def get_valid_access_token(session: Session, account: OAuthAccount) -> str:
    if (
        account.encrypted_access_token
        and account.access_token_expires_at
        and account.access_token_expires_at - _EXPIRY_SAFETY_MARGIN > utcnow()
    ):
        return decrypt_token(account.encrypted_access_token)

    if not account.encrypted_refresh_token:
        raise ReconnectNeededError(f"OAuthAccount {account.id} has no refresh token stored")

    refresh_token = decrypt_token(account.encrypted_refresh_token)

    if account.provider.value != "google":
        raise NotImplementedError(f"token refresh not implemented for provider {account.provider}")

    try:
        result = youtube.refresh_access_token(refresh_token)
    except InvalidGrantError as exc:
        account.needs_reconnect = True
        account.last_error = str(exc)
        account.updated_at = utcnow()
        session.add(account)
        session.commit()
        log_event(
            session,
            "oauth_reconnect_needed",
            f"YouTube account '{account.display_name}' needs to be reconnected: {exc}",
            level="warning",
        )
        raise ReconnectNeededError(str(exc)) from exc

    account.encrypted_access_token = encrypt_token(result["access_token"])
    account.access_token_expires_at = utcnow() + timedelta(seconds=result.get("expires_in", 3600))
    account.needs_reconnect = False
    account.last_error = None
    account.updated_at = utcnow()
    session.add(account)
    session.commit()

    return result["access_token"]
