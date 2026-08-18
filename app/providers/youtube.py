"""
Google OAuth + YouTube Data API v3 client (Phase 2). Verified against the
current official docs (August 2026) rather than memory/tutorials -- see
GOOGLE_OAUTH_SETUP.md for the sources and the platform quirks that shaped
this file, in particular:

- The Data API does not expose pixel width/height for a video anywhere.
  YouTubeVideo.width/height stay unset from sync; short detection instead
  reads width/height off `snippet.thumbnails` (which IS documented and
  does reflect the source video's aspect ratio).
- There's no `isShort` field. Detection is duration (<=180s, the official
  cutoff since October 2024) plus aspect ratio, with #shorts as a
  tie-breaker -- see `detect_short`.
- In OAuth consent "Testing" publishing status, Google expires refresh
  tokens for sensitive scopes (youtube.readonly included) after 7 days.
  `refresh_access_token` raises InvalidGrantError on that so callers can
  surface "reconnect needed" instead of failing sync silently forever.

Only this module talks to Google's HTTP endpoints -- routers and workers
go through the functions here, never the URLs directly.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import get_settings

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
API_BASE = "https://www.googleapis.com/youtube/v3"

# Read-only, least-privilege (section 6). A write scope (for publishing
# *to* YouTube) would be requested separately, later, only if that feature
# actually gets built.
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

SHORTS_MAX_DURATION_SECONDS = 180  # official cutoff since 2024-10-15


class InvalidGrantError(Exception):
    """Refresh token is dead (revoked, or the 7-day Testing-mode expiry).
    Caller's job: mark the OAuthAccount as needing reconnection, not retry."""


def redirect_uri() -> str:
    return f"{get_settings().base_url}/oauth/google/callback"


def build_authorize_url(state: str) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # required to get a refresh_token at all
        "prompt": "consent",  # force a fresh refresh_token even on re-auth
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    """Returns {access_token, refresh_token, expires_in, scope, token_type}.
    `refresh_token` is only present because we sent access_type=offline AND
    prompt=consent -- Google omits it on a repeat authorization otherwise."""
    settings = get_settings()
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Returns {access_token, expires_in, scope, token_type}. Raises
    InvalidGrantError if the refresh token is no longer valid."""
    settings = get_settings()
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "refresh_token": refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    if resp.status_code == 400 and resp.json().get("error") == "invalid_grant":
        raise InvalidGrantError("Google rejected the refresh token (revoked, or 7-day Testing-mode expiry)")
    resp.raise_for_status()
    return resp.json()


def revoke_token(token: str) -> None:
    """Best-effort; a token that's already dead 400s here, which is fine --
    the caller is disconnecting either way."""
    try:
        httpx.post(REVOKE_ENDPOINT, params={"token": token}, timeout=20)
    except httpx.HTTPError:
        pass


def _auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def get_own_channel(access_token: str) -> Optional[dict]:
    """The authenticated user's channel, with its uploads playlist ID --
    see https://developers.google.com/youtube/v3/docs/channels/list."""
    resp = httpx.get(
        f"{API_BASE}/channels",
        params={"part": "snippet,contentDetails", "mine": "true"},
        headers=_auth_headers(access_token),
        timeout=20,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return items[0] if items else None


def list_uploads_page(access_token: str, uploads_playlist_id: str, page_token: Optional[str] = None) -> dict:
    """One page (<=50) of {video_id, position} from the channel's uploads
    playlist. Returns the raw playlistItems.list response so the caller can
    read nextPageToken."""
    params = {"part": "contentDetails", "playlistId": uploads_playlist_id, "maxResults": 50}
    if page_token:
        params["pageToken"] = page_token
    resp = httpx.get(
        f"{API_BASE}/playlistItems",
        params=params,
        headers=_auth_headers(access_token),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def get_videos(access_token: str, video_ids: list[str]) -> list[dict]:
    """Full video resources (snippet + contentDetails + status) for up to
    50 IDs at a time -- the API's own batch limit."""
    if not video_ids:
        return []
    assert len(video_ids) <= 50, "videos.list accepts at most 50 ids per call"
    resp = httpx.get(
        f"{API_BASE}/videos",
        params={"part": "snippet,contentDetails,status", "id": ",".join(video_ids)},
        headers=_auth_headers(access_token),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


_ISO8601_DURATION_RE = re.compile(
    r"P(?:\d+D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?"
)


def parse_iso8601_duration(value: str) -> Optional[float]:
    """'PT1M30S' -> 90.0. YouTube durations are always in whole seconds."""
    if not value:
        return None
    match = _ISO8601_DURATION_RE.fullmatch(value)
    if not match:
        return None
    parts = match.groupdict()
    hours = int(parts["hours"] or 0)
    minutes = int(parts["minutes"] or 0)
    seconds = int(parts["seconds"] or 0)
    return float(hours * 3600 + minutes * 60 + seconds)


def parse_iso8601_datetime(value: str) -> Optional[datetime]:
    """'2026-01-15T10:00:00Z' -> naive UTC datetime (tzinfo stripped after
    conversion, to match app.models._util.utcnow's convention -- see its
    docstring for why: SQLite drops tzinfo on every stored datetime, so
    keeping this one aware would make it silently uncomparable to anything
    read back from the database)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


def _best_thumbnail_dimensions(thumbnails: dict) -> Optional[tuple[int, int]]:
    """Picks the highest-res thumbnail that actually has width/height (the
    API doesn't always return them). This is the only aspect-ratio signal
    the Data API gives us -- see the module docstring."""
    for size in ("maxres", "standard", "high", "medium", "default"):
        thumb = thumbnails.get(size)
        if thumb and thumb.get("width") and thumb.get("height"):
            return thumb["width"], thumb["height"]
    return None


def detect_short(video: dict) -> tuple[bool, str]:
    """(is_short, human-readable reason). Conservative by design: an
    ambiguous video is classified as NOT a Short rather than guessed True
    -- wrong "not a Short" is a one-click fix in the Library UI (section
    8), wrong "Short" silently queues something that shouldn't be there."""
    duration = parse_iso8601_duration(video.get("contentDetails", {}).get("duration", ""))
    if duration is None:
        return False, "duration unavailable from the API"
    if duration > SHORTS_MAX_DURATION_SECONDS:
        return False, f"duration {duration:.0f}s exceeds the {SHORTS_MAX_DURATION_SECONDS}s Shorts maximum"

    snippet = video.get("snippet", {})
    title = snippet.get("title", "")
    description = snippet.get("description", "")
    has_hashtag = "#shorts" in title.lower() or "#shorts" in description.lower()

    dims = _best_thumbnail_dimensions(snippet.get("thumbnails", {}))
    if dims:
        width, height = dims
        if height >= width:
            return True, f"duration {duration:.0f}s <= {SHORTS_MAX_DURATION_SECONDS}s and vertical/square thumbnail ({width}x{height})"
        if has_hashtag:
            return True, f"duration {duration:.0f}s <= {SHORTS_MAX_DURATION_SECONDS}s, landscape thumbnail ({width}x{height}) but #shorts tag present"
        return False, f"duration {duration:.0f}s <= {SHORTS_MAX_DURATION_SECONDS}s but landscape thumbnail ({width}x{height})"

    if has_hashtag:
        return True, f"duration {duration:.0f}s <= {SHORTS_MAX_DURATION_SECONDS}s and #shorts tag present (no thumbnail dimensions available)"
    return False, f"duration {duration:.0f}s <= {SHORTS_MAX_DURATION_SECONDS}s but no aspect-ratio or #shorts signal -- verify manually"
