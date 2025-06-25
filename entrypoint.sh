#!/usr/bin/env bash
set -e

echo "[Entrypoint] Migrating database…"
python manage.py migrate --noinput

echo "[Entrypoint] Collecting static files…"
python manage.py collectstatic --noinput

echo "[Entrypoint] Starting application…"
exec "$@"

