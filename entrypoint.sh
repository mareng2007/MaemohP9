#!/bin/bash
set -e

echo "[Entrypoint] Migrating database…"
python manage.py migrate --noinput

echo "[Entrypoint] Collecting static files…"
python manage.py collectstatic --noinput

# สุดท้าย exec คำสั่งที่ส่งเข้ามาจาก CMD หรือ docker-compose
exec "$@"

