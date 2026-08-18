# Troubleshooting

## `/health` returns `"database": "error: ..."`

Check `docker compose logs shortbridge`. `data` is a named volume
(`shortbridge_data`) that Docker initializes with the image's uid-1000
ownership, so this shouldn't be a permissions problem in normal operation
— if it is (e.g. after manually poking at the volume), fix with:
`docker run --rm -v shortbridge_data:/data alpine chown -R 1000:1000 /data`.

## `/health` returns `"scheduler": "stopped"`

The APScheduler background scheduler didn't start — check the container
logs around the "Adding job" / "Scheduler started" lines. If it crashed on
startup, `/` and other pages will still 500 since `init_db()` runs in the
same lifespan block.

## Can't log in / forgot admin password

Regenerate: `python scripts/hash_password.py`, update `ADMIN_PASSWORD_HASH`
in `.env`, `docker compose up -d` (recreates the container; `ensure_admin_user`
syncs the DB row to the new hash on the next startup).

## Locked out by the login rate limiter

It's in-memory, keyed by IP, and resets on container restart:
`docker compose restart shortbridge`. Or just wait out the window
(`LOGIN_RATE_LIMIT_WINDOW_SECONDS`, default 5 minutes).

## "database is locked" errors

Should not happen in normal operation (WAL mode + `busy_timeout=30000` in
`app/database.py`), but if it does: check nothing else has `data/shortbridge.db`
open (a stray `sqlite3` shell, an editor with a lock, etc.), and confirm
the volume isn't NFS or similar (SQLite WAL mode needs a filesystem with
proper POSIX locking — a plain Docker bind mount on ext4/local disk, which
is what this VPS uses, is fine).

## Traefik isn't issuing a certificate / 404s at the domain

Check `docker compose -f /docker/traefik/docker-compose.yml logs traefik`
for ACME errors. Common causes: the `traefik.enable=true` label is missing
or the container isn't actually running, or DNS for the host doesn't point
at this VPS yet (not an issue for the default
`shortbridge.srv1006990.hstgr.cloud` host — that resolves automatically).

## Rolling back a bad deploy

```
cd /docker/shortbridge
git log --oneline -5
git checkout <previous-good-commit>
docker compose build
docker compose up -d
curl -f https://shortbridge.srv1006990.hstgr.cloud/health
```

If the schema also needs rolling back: `docker compose exec shortbridge
alembic downgrade -1` before switching the code back (migrations here are
written with `render_as_batch=True` so SQLite `ALTER TABLE` limitations
don't block this).
