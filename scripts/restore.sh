#!/usr/bin/env bash
# Restores database + .env from a backup.sh archive into the named
# `shortbridge_data` volume. Stops the app first (SQLite must not be
# written to during restore) -- this is a maintenance action, announce
# downtime before running it against production.
set -euo pipefail
cd "$(dirname "$0")/.."

ARCHIVE="${1:-}"
if [[ -z "$ARCHIVE" || ! -f "$ARCHIVE" ]]; then
    echo "Usage: $0 <path-to-backup.tar.gz>" >&2
    echo "Available backups:" >&2
    ls -1t backups/shortbridge-*.tar.gz 2>/dev/null >&2 || true
    exit 1
fi

read -r -p "This will stop shortbridge and overwrite the shortbridge_data volume and .env from ${ARCHIVE}. Continue? [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 1
fi

docker compose down

STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
tar -xzf "$ARCHIVE" -C "$STAGING"

cp "$STAGING"/.env .env

docker volume create shortbridge_data >/dev/null
# Wipe the volume first so a restore onto an existing (partially written)
# volume can't leave stale files mixed in with the restored ones.
docker run --rm -v shortbridge_data:/to alpine sh -c "rm -rf /to/* /to/.[!.]* 2>/dev/null; true"
docker run --rm -v shortbridge_data:/to -v "$STAGING":/from:ro \
    alpine sh -c "tar -xzf /from/data.tar.gz -C /to"

docker compose up -d
echo "Restore complete. Check: docker compose logs -f shortbridge, then curl -f https://<host>/health"
