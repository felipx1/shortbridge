"""
Central application settings, loaded from environment variables (.env in dev,
real env vars in the Docker Compose deployment).

Nothing secret has a default value that would work in production -- if a
required secret is missing, the app refuses to start rather than falling
back to something insecure.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    app_name: str = "ShortBridge"
    base_url: str = "https://shortbridge.srv1006990.hstgr.cloud"
    timezone: str = "America/Santiago"
    dry_run: bool = True

    # --- Storage paths (inside the container) ---
    data_dir: Path = Path("/data")
    media_dir: Path = Path("/media")

    @property
    def database_path(self) -> Path:
        return self.data_dir / "shortbridge.db"

    @property
    def media_inbox_dir(self) -> Path:
        return self.media_dir / "inbox"

    @property
    def media_import_dir(self) -> Path:
        return self.media_dir / "import"

    @property
    def media_processed_dir(self) -> Path:
        return self.media_dir / "processed"

    @property
    def media_youtube_dir(self) -> Path:
        """Where yt-dlp writes downloads, when enabled below."""
        return self.media_dir / "youtube"

    # --- Secrets (required, no safe default) ---
    app_secret_key: str  # signs session cookies + CSRF tokens
    app_encryption_key: str  # encrypts OAuth tokens at rest (Fernet key, 32 url-safe base64 bytes)

    # --- Admin auth ---
    admin_username: str = "admin"
    admin_password_hash: str  # Argon2id hash, generated once via scripts/hash_password.py

    session_cookie_name: str = "shortbridge_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 14  # 14 days
    # Only ever set to false for local http:// development. Production
    # (behind Traefik/HTTPS) must keep this true -- see section 23.
    cookie_secure: bool = True

    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    # --- Google / YouTube (filled in Phase 2) ---
    google_client_id: str = ""
    google_client_secret: str = ""

    # --- TikTok (filled in Phase 4) ---
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""

    # --- Scheduler ---
    youtube_sync_interval_hours: int = 6

    # --- Unofficial YouTube download (yt-dlp), OFF by default. See
    # UNOFFICIAL_DOWNLOAD.md before turning this on: not the official Data
    # API, technically against YouTube's Terms of Service, and can break
    # without warning whenever YouTube changes its internals. Explicit
    # opt-in only -- never silently active. ---
    enable_youtube_unofficial_download: bool = False
    # Seconds to wait between each background download -- paces requests
    # instead of bursting through the whole backlog at once (section 33's
    # "no hagas polling agresivo" spirit, doubly true for an unofficial
    # mechanism where bursty traffic is more likely to get flagged).
    youtube_download_interval_seconds: int = 15
    # Don't retry a failed download (private/deleted/age-restricted/etc.)
    # again for this long -- avoids hot-looping on a permanently broken video.
    youtube_download_retry_after_hours: int = 6

    # --- Home download agent (scripts/agent/) ---
    # YouTube's bot detection treats this VPS's datacenter IP far more
    # aggressively than a residential one (confirmed in production -- see
    # UNOFFICIAL_DOWNLOAD.md). The agent runs yt-dlp on a residential
    # connection instead and pushes finished files here. Blank = the
    # agent endpoints are disabled (401 on everything) -- generate with
    # `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
    agent_api_token: str = ""

    @property
    def is_google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def is_tiktok_configured(self) -> bool:
        return bool(self.tiktok_client_key and self.tiktok_client_secret)

    @property
    def is_agent_configured(self) -> bool:
        return bool(self.agent_api_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
