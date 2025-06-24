#!/usr/bin/env bash
set -e

echo "[Entrypoint] Making migrations & migrating database…"
python manage.py makemigrations --noinput
python manage.py migrate    --noinput

exec "$@"
