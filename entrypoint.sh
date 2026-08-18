#!/usr/bin/env bash
# Runs pending Alembic migrations before starting the app. This is what
# "docker compose up -d" actually applying schema changes means in
# practice (section 29) -- no manual migration step on deploy.
set -euo pipefail

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
