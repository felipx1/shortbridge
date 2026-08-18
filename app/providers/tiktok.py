"""
TikTok Login Kit (OAuth v2) client (Phase 4). Verified against the
current official docs (August 2026) rather than memory/tutorials -- see
TIKTOK_SETUP.md for the sources and platform specifics that shaped this
file:

- No PKCE for the web server flow (only required for desktop/mobile apps).
- `scope` is comma-separated (Google's is space-separated -- easy to get
  backwards).
- Token refresh can return a NEW refresh_token that must replace the
  stored one -- unlike Google, which normally only issues one on first
  consent. app.services.oauth handles this generically (updates
  encrypted_refresh_token whenever a refresh response includes one, for
  any provider).
- Access tokens last 24h, refresh tokens last 365 days -- no Google-style
  "7-day Testing-mode" trap here, but the app itself starts in unaudited
  Sandbox mode: content posted through the Content Posting API is forced
  private regardless of the requested visibility until the app passes
  TikTok's review (section 40/Phase 9). Doesn't affect OAuth itself.
- Requesting a scope your app hasn't had that scope's product (Login Kit
  covers user.info.basic; Content Posting API covers video.list/upload/
  publish) added to in the developer portal fails outright -- there's no
  silent partial grant at the request stage the way Google can grant a
  subset. What IS possible: video.publish specifically staying
  audit-gated (private-only) even once granted -- see connections.html,
  which reflects granted_scopes rather than assuming the full SCOPES list
  was actually approved.

Only this module talks to TikTok's HTTP endpoints -- routers and workers
go through the functions here, never the URLs directly.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.providers.base import ProviderInvalidGrantError

AUTH_ENDPOINT = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_ENDPOINT = "https://open.tiktokapis.com/v2/oauth/token/"
REVOKE_ENDPOINT = "https://open.tiktokapis.com/v2/oauth/revoke/"
API_BASE = "https://open.tiktokapis.com/v2"

# Requested upfront (section 12); what's actually usable is whatever
# comes back in granted_scopes -- the UI (connections.html) reflects that,
# not this list, since video.publish in particular may not be approved yet.
SCOPES = ["user.info.basic", "video.list", "video.upload", "video.publish"]


class InvalidGrantError(ProviderInvalidGrantError):
    """Refresh token is dead (revoked, or past its 365-day life). Caller's
    job: mark the OAuthAccount as needing reconnection, not retry."""


def redirect_uri() -> str:
    return f"{get_settings().base_url}/oauth/tiktok/callback"


def build_authorize_url(state: str) -> str:
    settings = get_settings()
    params = {
        "client_key": settings.tiktok_client_key,
        "redirect_uri": redirect_uri(),
        "scope": ",".join(SCOPES),  # comma-separated -- NOT space-separated like Google
        "response_type": "code",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def _post_token_request(data: dict) -> dict:
    settings = get_settings()
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={"client_key": settings.tiktok_client_key, "client_secret": settings.tiktok_client_secret, **data},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    body = resp.json() if resp.content else {}
    # Defensive on both fronts: TikTok v2 claims RFC 6749 (proper HTTP
    # status codes) but older TikTok APIs return 200 with an embedded
    # "error" field -- handle whichever shows up.
    error = body.get("error")
    if resp.status_code >= 400 or error:
        message = body.get("error_description") or str(error) or f"HTTP {resp.status_code}"
        if error in ("invalid_grant", "invalid_token") or resp.status_code in (400, 401):
            raise InvalidGrantError(message)
        raise RuntimeError(f"TikTok token endpoint error: {message}")
    return body


def exchange_code_for_tokens(code: str) -> dict:
    """Returns {access_token, refresh_token, expires_in, refresh_expires_in,
    open_id, scope, token_type}."""
    return _post_token_request({
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri(),
    })


def refresh_access_token(refresh_token: str) -> dict:
    """Returns the same shape as exchange_code_for_tokens. IMPORTANT: the
    response's refresh_token may differ from the one passed in -- callers
    must persist it if present (app.services.oauth does this generically).
    Raises InvalidGrantError if the refresh token is no longer valid."""
    return _post_token_request({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })


def revoke_token(access_token: str) -> None:
    """Best-effort; a token that's already dead errors here, which is
    fine -- the caller is disconnecting either way."""
    settings = get_settings()
    try:
        httpx.post(
            REVOKE_ENDPOINT,
            data={"client_key": settings.tiktok_client_key, "client_secret": settings.tiktok_client_secret, "token": access_token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
    except httpx.HTTPError:
        pass


def get_user_info(access_token: str) -> Optional[dict]:
    """{open_id, display_name, avatar_url} for the connected account --
    requires user.info.basic. See
    https://developers.tiktok.com/doc/tiktok-api-v2-get-user-info."""
    resp = httpx.get(
        f"{API_BASE}/user/info/",
        params={"fields": "open_id,display_name,avatar_url"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get("data", {}).get("user")
