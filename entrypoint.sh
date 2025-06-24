#!/usr/bin/env bash
set -e

echo "[Entrypoint] Making migrations & migrating database…"
# สร้างไฟล์ migrations สำหรับทุก app (ถ้าไม่มี) แล้วรัน migrate
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "[Entrypoint] Collecting static files…"
python manage.py collectstatic --noinput

echo "[Entrypoint] Starting application…"
# exec จะเอา CMD จาก Dockerfile (หรือ override จาก compose) มา run ต่อ
exec "$@"

