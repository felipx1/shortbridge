"""Not a pytest suite -- a quick manual smoke test for Phase 1, run once
locally to prove the app boots and the auth flow works end to end before
touching the VPS. Section 34 wants real tests; this is the first one."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.__enter__()  # trigger the lifespan (init_db, ensure_admin_user, start_scheduler)

# /health should work with no login
r = client.get("/health")
assert r.status_code == 200, r.text
print("GET /health ->", r.status_code, r.json())

# Dashboard requires login -> redirected to /login
r = client.get("/", follow_redirects=False)
assert r.status_code == 303, (r.status_code, r.text)
assert r.headers["location"] == "/login"
print("GET / (no session) -> 303 to /login  OK")

# Login page renders and contains a csrf token
r = client.get("/login")
assert r.status_code == 200
assert "csrf_token" in r.text
import re
csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
print("GET /login -> 200, csrf token extracted")

# Wrong password -> 400, no cookie set
r = client.post("/login", data={"username": "admin", "password": "wrong", "csrf_token": csrf})
assert r.status_code == 400, r.status_code
print("POST /login (wrong password) -> 400  OK")

# Correct login (matches ADMIN_PASSWORD_HASH generated for 'dev-only-password' in .env)
r2 = client.get("/login")
csrf2 = re.search(r'name="csrf_token" value="([^"]+)"', r2.text).group(1)
r = client.post("/login", data={"username": "admin", "password": "dev-only-password", "csrf_token": csrf2}, follow_redirects=False)
assert r.status_code == 303, (r.status_code, r.text)
assert "shortbridge_session" in r.cookies
print("POST /login (correct password) -> 303, session cookie set  OK")

# Now dashboard should load
r = client.get("/")
assert r.status_code == 200, r.text
assert "Dashboard" in r.text
assert "DRY RUN MODE" in r.text
print("GET / (logged in) -> 200, dashboard renders, DRY RUN banner present  OK")

# Other pages
for path in ["/connections", "/library", "/queue", "/settings", "/logs"]:
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code, r.text[:300])
    print(f"GET {path} -> 200  OK")

# Settings POST round-trip (with CSRF)
r = client.get("/settings")
csrf3 = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
r = client.post("/settings", data={
    "csrf_token": csrf3, "daily_times": "09:00,14:00,19:00", "timezone": "America/Santiago",
    "monday": "on", "tuesday": "on", "wednesday": "on", "thursday": "on", "friday": "on",
}, follow_redirects=False)
assert r.status_code == 303, (r.status_code, r.text)
r = client.get("/settings")
assert "09:00,14:00,19:00" in r.text
print("POST /settings -> schedule persisted  OK")

# Logout
r = client.post("/logout", follow_redirects=False)
assert r.status_code == 303
print("POST /logout -> 303  OK")

print("\nALL SMOKE TESTS PASSED")
