"""Manual smoke test for Phase 4 (TikTok OAuth) pieces that don't require
real TikTok credentials: authorize URL shape, the app refusing to start
TikTok OAuth when unconfigured, and the token-endpoint error parsing
(mocked httpx responses -- covers both the "proper HTTP status" and the
"200 with an embedded error field" shapes TikTok might return, since the
docs didn't pin this down precisely). The actual OAuth dance can only be
verified against a real TikTok app -- see TIKTOK_SETUP.md."""
from unittest.mock import patch

import httpx

from app.providers import tiktok

# --- Authorize URL ---
url = tiktok.build_authorize_url("teststate123")
assert "client_key=" in url
assert "response_type=code" in url
assert "state=teststate123" in url
# comma-separated, NOT space-separated (space would be %20 or + here) --
# this is the opposite of Google's scope format, easy to get backwards.
assert "video.upload%2Cvideo.publish" in url or "video.upload,video.publish" in url
assert "%20" not in url.split("scope=")[1].split("&")[0]
print("authorize URL (comma-separated scopes, no PKCE params):", url)


def _fake_response(status_code: int, json_body: dict) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=json_body, request=httpx.Request("POST", tiktok.TOKEN_ENDPOINT))


# --- Error parsing: proper HTTP 400 + invalid_grant ---
with patch("httpx.post", return_value=_fake_response(400, {"error": "invalid_grant", "error_description": "expired"})):
    try:
        tiktok.refresh_access_token("dead-token")
        raise AssertionError("expected InvalidGrantError")
    except tiktok.InvalidGrantError:
        print("HTTP 400 + invalid_grant -> InvalidGrantError  OK")

# --- Error parsing: 200 with an embedded error field (older-API-style shape) ---
with patch("httpx.post", return_value=_fake_response(200, {"error": "invalid_grant", "error_description": "revoked"})):
    try:
        tiktok.refresh_access_token("dead-token")
        raise AssertionError("expected InvalidGrantError")
    except tiktok.InvalidGrantError:
        print("HTTP 200 + embedded invalid_grant -> InvalidGrantError  OK")

# --- Successful refresh, including the token-rotation quirk ---
with patch(
    "httpx.post",
    return_value=_fake_response(200, {"access_token": "new-at", "refresh_token": "new-rt", "expires_in": 86400}),
):
    result = tiktok.refresh_access_token("old-rt")
    assert result["access_token"] == "new-at"
    assert result["refresh_token"] == "new-rt"  # caller must persist this -- see app.services.oauth
    print("Successful refresh returns a (possibly new) refresh_token  OK")

# --- App refuses to start OAuth when TikTok isn't configured ---
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

with TestClient(app) as client:
    r = client.get("/login")
    import re

    csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    client.post("/login", data={"username": "admin", "password": "dev-only-password", "csrf_token": csrf})

    r = client.get("/oauth/tiktok/start", follow_redirects=False)
    assert r.status_code == 400, (r.status_code, r.text)
    print("GET /oauth/tiktok/start with no credentials configured -> 400  OK")

    r = client.get("/connections")
    assert "No TikTok app credentials set yet" in r.text
    print("GET /connections shows 'Not configured' for TikTok  OK")

print("\nALL PHASE 4 SMOKE TESTS PASSED")
