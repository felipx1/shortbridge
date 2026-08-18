# ShortBridge

Self-hosted YouTube Shorts → TikTok bridge. Connects your own YouTube
channel and TikTok account via their official OAuth APIs, keeps a library
of your Shorts, and publishes them to TikTok (draft first, direct post once
TikTok approves it) on a schedule you control. No SaaS, no scraping, no
browser automation — official APIs only.

## Status

Phase 1 of 10 complete: project skeleton, auth, database, scheduler
skeleton, UI shell. YouTube and TikTok are not connected yet — see
`PROGRESS.md` for what's done and what's next.

## Stack

FastAPI + SQLModel (SQLite, WAL mode) + Alembic + APScheduler + Jinja2,
running in a single Docker container behind the Traefik reverse proxy
already installed on the target VPS. No Redis, no Celery, no Kubernetes —
see `CONFIGURATION.md` for why.

## Local development

```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python scripts\generate_keys.py  # paste output into .env
python scripts\hash_password.py  # paste output into .env
# fill in .env from .env.example, using COOKIE_SECURE=false for http:// dev
alembic upgrade head
uvicorn app.main:app --reload
```

## Deployment

See `INSTALL.md`. Deployed on the VPS as a Docker Compose project at
`/docker/shortbridge/`, managed the same way the other projects on that
VPS are.

## Docs

- `INSTALL.md` — first deployment
- `CONFIGURATION.md` — environment variables, architecture decisions
- `GOOGLE_OAUTH_SETUP.md` / `TIKTOK_SETUP.md` — creating the OAuth apps (Phase 2 / Phase 4)
- `BACKUP_RESTORE.md`
- `TROUBLESHOOTING.md`
