#!/usr/bin/env bash
# Backs up the database and configuration (section 28). Run from the
# project root (/docker/shortbridge on the VPS). Media files are NOT
# included here -- back those up separately if/when the library gets large
# (they're reproducible from YouTube/your own archive; the DB and .env are
# not).
set -euo pipefail
cd "$(dirname "$0")/.."

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="backups"
OUT="${BACKUP_DIR}/shortbridge-${TIMESTAMP}.tar.gz"
KEEP=14

mkdir -p "$BACKUP_DIR"

# sqlite3 .backup would be ideal for a live DB, but a plain WAL-mode copy of
# the three db files is safe as long as nothing is mid-transaction; a few
# seconds of downtime risk is acceptable for a daily cron backup here.
tar -czf "$OUT" \
    --ignore-failed-read \
    data/shortbridge.db data/shortbridge.db-wal data/shortbridge.db-shm \
    .env

echo "Backup written to $OUT"

# Prune old backups, keep the most recent $KEEP
ls -1t "${BACKUP_DIR}"/shortbridge-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm --
