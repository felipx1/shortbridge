#!/usr/bin/env bash
# Restores database + .env from a backup.sh archive. Stops the app first
# (SQLite must not be written to during restore), so this is a maintenance
# action -- announce downtime before running it against production.
set -euo pipefail
cd "$(dirname "$0")/.."

ARCHIVE="${1:-}"
if [[ -z "$ARCHIVE" || ! -f "$ARCHIVE" ]]; then
    echo "Usage: $0 <path-to-backup.tar.gz>" >&2
    echo "Available backups:" >&2
    ls -1t backups/shortbridge-*.tar.gz 2>/dev/null >&2 || true
    exit 1
fi

read -r -p "This will stop shortbridge and overwrite data/ and .env from ${ARCHIVE}. Continue? [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 1
fi

docker compose down

mkdir -p data
tar -xzf "$ARCHIVE"

docker compose up -d
echo "Restore complete. Check: docker compose logs -f shortbridge, then curl -f https://<host>/health"
