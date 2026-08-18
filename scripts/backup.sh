#!/usr/bin/env bash
# Backs up the database and configuration (section 28). Run from the
# project root (/docker/shortbridge on the VPS). `data` is a named Docker
# volume (not a bind mount, see docker-compose.yml), so we back it up via a
# throwaway container rather than tar-ing a host path directly. Media files
# are NOT included here -- back those up separately if/when the library
# gets large (they're reproducible from YouTube/your own archive; the DB
# and .env are not).
set -euo pipefail
cd "$(dirname "$0")/.."

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="backups"
OUT="${BACKUP_DIR}/shortbridge-${TIMESTAMP}.tar.gz"
KEEP=14

mkdir -p "$BACKUP_DIR"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

docker run --rm \
    -v shortbridge_data:/from:ro \
    -v "${STAGING}":/to \
    alpine sh -c "cd /from && tar -czf /to/data.tar.gz ."

cp .env "$STAGING"/.env

tar -czf "$OUT" -C "$STAGING" data.tar.gz .env
echo "Backup written to $OUT"

# Prune old backups, keep the most recent $KEEP
ls -1t "${BACKUP_DIR}"/shortbridge-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm --
