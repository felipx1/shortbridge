"""Manual smoke test for Phase 2 (Google OAuth + YouTube sync) pieces that
don't require real Google credentials: the short-detection heuristic, ISO
8601 duration parsing, and that the app correctly refuses to start an
OAuth flow when Google isn't configured yet. The actual OAuth dance
(authorize -> callback -> token exchange) can only be verified against a
real Google Cloud project -- see GOOGLE_OAUTH_SETUP.md for the one-video,
one-account manual test to run once credentials are in .env."""
from app.providers import youtube

# --- ISO 8601 duration parsing ---
assert youtube.parse_iso8601_duration("PT1M30S") == 90.0
assert youtube.parse_iso8601_duration("PT45S") == 45.0
assert youtube.parse_iso8601_duration("PT3M") == 180.0
assert youtube.parse_iso8601_duration("PT1H2M3S") == 3723.0
assert youtube.parse_iso8601_duration("") is None
assert youtube.parse_iso8601_duration("garbage") is None
print("parse_iso8601_duration: OK")

# --- Short detection ---


def video(duration, width=None, height=None, title="", description="", rotation=None, no_file_details=False):
    file_details = {}
    if not no_file_details and width and height:
        stream = {"widthPixels": width, "heightPixels": height}
        if rotation:
            stream["rotation"] = rotation
        file_details = {"videoStreams": [stream]}
    return {
        "contentDetails": {"duration": duration},
        "snippet": {"title": title, "description": description, "thumbnails": {}},
        "fileDetails": file_details,
    }


# Vertical, 45s -> Short (real fileDetails pixel dims, not the useless thumbnail signal)
is_short, reason = youtube.detect_short(video("PT45S", 1080, 1920))
assert is_short is True, reason
print("vertical 45s -> Short:", reason)

# Landscape, 45s, no hashtag -> not a Short
is_short, reason = youtube.detect_short(video("PT45S", 1920, 1080))
assert is_short is False, reason
print("landscape 45s, no tag -> not Short:", reason)

# Landscape, 45s, WITH #shorts hashtag -> Short (tie-breaker)
is_short, reason = youtube.detect_short(video("PT45S", 1920, 1080, title="My clip #shorts"))
assert is_short is True, reason
print("landscape 45s, #shorts tag -> Short:", reason)

# Phone-recorded vertical video stored as a landscape file (1920x1080) but
# flagged 90-degree rotated -> effective dims are 1080x1920, still a Short
is_short, reason = youtube.detect_short(video("PT45S", 1920, 1080, rotation="clockwise"))
assert is_short is True, reason
print("landscape file + clockwise rotation -> Short:", reason)

# 200s (over the 180s cap) even if vertical -> never a Short
is_short, reason = youtube.detect_short(video("PT3M20S", 1080, 1920))
assert is_short is False, reason
print("vertical 200s (>180s cap) -> not Short:", reason)

# Exactly 180s, vertical -> Short (boundary is inclusive)
is_short, reason = youtube.detect_short(video("PT3M", 1080, 1920))
assert is_short is True, reason
print("vertical exactly 180s -> Short:", reason)

# fileDetails unavailable (e.g. part rejected, or empty for this real
# channel's videos -- this is the exact case that misclassified 253 real
# Shorts as "not a Short" when the signal used to be thumbnail dimensions),
# no hashtag, short duration -> duration alone is trusted
is_short, reason = youtube.detect_short(video("PT30S", no_file_details=True))
assert is_short is True, reason
print("no fileDetails, no tag, short duration -> Short (duration-only fallback):", reason)

# fileDetails unavailable but #shorts tag present -> Short
is_short, reason = youtube.detect_short(video("PT30S", title="#shorts", no_file_details=True))
assert is_short is True, reason
print("no fileDetails, #shorts tag -> Short:", reason)

print("\nauthorize URL (should include client_id, scope, state, access_type=offline, prompt=consent):")
url = youtube.build_authorize_url("teststate123")
assert "access_type=offline" in url
assert "prompt=consent" in url
assert "state=teststate123" in url
assert "youtube.readonly" in url
print(url)

# --- App refuses to start OAuth when Google isn't configured ---
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

with TestClient(app) as client:
    r = client.get("/login")
    import re

    csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    client.post("/login", data={"username": "admin", "password": "dev-only-password", "csrf_token": csrf})

    r = client.get("/oauth/google/start", follow_redirects=False)
    # GOOGLE_CLIENT_ID/SECRET are blank in the local .env -> should refuse cleanly
    assert r.status_code == 400, (r.status_code, r.text)
    print("GET /oauth/google/start with no credentials configured -> 400  OK")

    r = client.get("/connections")
    assert "Not configured" in r.text
    print("GET /connections shows 'Not configured' for Google  OK")

print("\nALL PHASE 2 SMOKE TESTS PASSED")
