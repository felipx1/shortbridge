"""
Encryption at rest for OAuth tokens (section 24). Uses Fernet (AES-128-CBC +
HMAC, from the `cryptography` package) keyed by APP_ENCRYPTION_KEY. This is
deliberately simple -- no KMS integration -- because the threat this
defends against is "someone reads the SQLite file or a DB backup", not
"someone has root on the container" (if they have that, they can read the
key from the environment anyway; no amount of app-layer crypto fixes that).
"""
from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.app_encryption_key.encode())


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
