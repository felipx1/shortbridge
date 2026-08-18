# Backup & Restore

## What's backed up

`scripts/backup.sh` archives:
- `data/shortbridge.db` (+ `-wal`/`-shm` if present)
- `.env` (secrets + config)

Media files are **not** included — they're large and, for Shorts sourced
from YouTube, reproducible. If your library is mostly `IMPORT_ARCHIVE`
media with no other copy, back up `media/` separately with your own
tooling (rsync to another host, etc.) — it's outside `backup.sh`'s scope
on purpose (section 28).

## Running a backup

```
cd /docker/shortbridge
./scripts/backup.sh
```

Writes `backups/shortbridge-<UTC timestamp>.tar.gz`, keeps the most recent
14. Put this on a daily cron job once Phase 10 wraps up.

## Restoring

```
cd /docker/shortbridge
./scripts/restore.sh backups/shortbridge-20260101T000000Z.tar.gz
```

This stops the app, overwrites `data/` and `.env`, and starts it back up.
There is a confirmation prompt — this is destructive to whatever is
currently in `data/`.

After restoring, re-check ownership (containers run as uid 1000, see
`INSTALL.md` step 3) and hit `/health`.
