#!/usr/bin/env bash
set -e

echo "[Entrypoint] Making migrations…"
python manage.py makemigrations --noinput

echo "[Entrypoint] Migrating database…"
python manage.py migrate --noinput

echo "[Entrypoint] Collecting static files…"
python manage.py collectstatic --noinput

echo "[Entrypoint] Starting application…"
exec "$@"
