# Configuration

## Environment variables

All settings live in `.env` (see `.env.example` for the full list with
comments). Key ones:

| Variable | Meaning |
|---|---|
| `BASE_URL` | Public HTTPS URL of this deployment. Used to build OAuth redirect URIs. |
| `DRY_RUN` | `true` = sync/process/schedule normally but never call TikTok's publish endpoint. Keep this `true` until you've tested with one throwaway video. |
| `APP_SECRET_KEY` | Signs session cookies and CSRF tokens. Rotating logs everyone out. |
| `APP_ENCRYPTION_KEY` | Fernet key encrypting OAuth tokens at rest. Rotating makes existing stored tokens unreadable — you'd have to reconnect YouTube/TikTok. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` | Single admin login (section 23). Regenerate the hash with `scripts/hash_password.py`. |
| `COOKIE_SECURE` | Must be `true` in production (HTTPS via Traefik). Only `false` for local `http://` dev. |

## Why this stack, not something bigger

- **SQLite (WAL mode), not Postgres**: single-writer workload, single
  instance, easy backup (copy 3 files). WAL mode lets the scheduler and web
  process both touch it without lock contention.
- **APScheduler in-process, not Celery+Redis**: one background worker is
  enough for "sync every N hours" + "check due publications every minute."
  Adding a broker would be complexity with no corresponding need at this
  scale. Revisit only if ShortBridge ever needs more than one web replica.
- **Traefik, not a second reverse proxy**: the target VPS already runs
  Traefik for other projects (label-based routing, automatic Let's Encrypt).
  ShortBridge just adds Docker labels to the same instance.
- **Signed cookie sessions, not a session store**: single admin user, no
  need for server-side session invalidation beyond "rotate `APP_SECRET_KEY`."

## Architecture

```
app/
  providers/    YouTube and TikTok API clients, behind a shared interface
                (providers/base.py) so Instagram/Facebook can be added later
                without touching routers or workers.
  services/     scheduler.py, crypto.py, audit.py, (media.py, oauth.py,
                duplicate_detector.py land in Phase 2-6)
  models/       SQLModel tables (see section 31 of the original spec)
  workers/      sync.py (YouTube), publisher.py (TikTok) -- APScheduler jobs
  routers/      one file per screen (dashboard, connections, library, queue,
                settings, logs) + auth + health
  templates/    Jinja2, server-rendered, no JS framework
```

## Timezone handling

Everything is stored in UTC. `Schedule.timezone` (default
`America/Santiago`) is only applied when converting local wall-clock times
(e.g. "20:00") to the next UTC run time, using the IANA tz database — so
daylight saving transitions are handled correctly, not with a hardcoded
offset.
