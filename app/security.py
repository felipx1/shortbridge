"""
Admin authentication primitives (section 23): Argon2id password hashing,
signed session cookies, and CSRF tokens. No external session store -- the
signed cookie *is* the session, which is fine for a single-admin app and
avoids adding Redis for no real benefit.
"""
from __future__ import annotations

import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

_hasher = PasswordHasher()


def hash_password(plaintext: str) -> str:
    return _hasher.hash(plaintext)


def verify_password(plaintext: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plaintext)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.app_secret_key, salt="shortbridge-session")


def create_session_token(user_id: int) -> str:
    return _serializer().dumps({"uid": user_id})


def read_session_token(token: str) -> int | None:
    settings = get_settings()
    try:
        data = _serializer().loads(token, max_age=settings.session_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("uid")


def _csrf_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.app_secret_key, salt="shortbridge-csrf")


def create_csrf_token() -> str:
    return _csrf_serializer().dumps(secrets.token_urlsafe(16))


def verify_csrf_token(token: str | None, max_age_seconds: int = 60 * 60 * 4) -> bool:
    if not token:
        return False
    try:
        _csrf_serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return False
    return True


def _oauth_state_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.app_secret_key, salt="shortbridge-oauth-state")


def create_oauth_state(provider: str, next_path: str = "/connections") -> str:
    """Signed, self-contained `state` param for an OAuth authorize request
    (sections 6, 12). No server-side session needed to validate it later --
    the signature + short expiry is the anti-CSRF protection, and
    `next_path` rides along so the callback knows where to send the user
    back without needing to store anything."""
    return _oauth_state_serializer().dumps({"provider": provider, "next": next_path})


def read_oauth_state(token: str, expected_provider: str, max_age_seconds: int = 600) -> str | None:
    """Returns `next_path` if the state is valid, freshly issued, and for
    the expected provider -- None otherwise (caller should reject the
    callback outright, never guess)."""
    try:
        data = _oauth_state_serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if data.get("provider") != expected_provider:
        return None
    return data.get("next", "/connections")


class LoginRateLimiter:
    """In-memory sliding-window limiter keyed by client IP. Resets on
    restart -- acceptable here since a restart is a rare, deliberate event
    and the real backstop against brute force is Argon2id's cost, not this."""

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}

    def is_blocked(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        attempts = [t for t in self._attempts.get(key, []) if t >= window_start]
        self._attempts[key] = attempts
        return len(attempts) >= self.max_attempts

    def record_attempt(self, key: str) -> None:
        self._attempts.setdefault(key, []).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


_settings = get_settings()
login_rate_limiter = LoginRateLimiter(
    max_attempts=_settings.login_rate_limit_attempts,
    window_seconds=_settings.login_rate_limit_window_seconds,
)
