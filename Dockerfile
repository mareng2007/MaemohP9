# --- Builder stage ---
FROM python:3.10-slim AS builder
WORKDIR /app

# ติดตั้ง OS deps สำหรับ build (libpq-dev, build-essential)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# สร้าง venv และติดตั้ง Python deps
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดเข้าไป
COPY . .

# ทำ migrations อัตโนมัติ (ไม่บังคับ แต่ช่วยให้ schema พร้อม)
RUN python manage.py makemigrations --noinput

# รัน collectstatic ตอน build
RUN python manage.py collectstatic --noinput

# --- Runtime stage ---
FROM python:3.10-slim AS runtime
WORKDIR /app

# ติดตั้ง runtime-only libs (libpq5)
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/*

# นำ venv จาก builder มาต่อ
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# นำโค้ดและ staticfiles ที่สร้างไว้ ไปใส่ใน runtime image
COPY --from=builder /app /app

# ติดตั้ง entrypoint script (ซึ่งตอนนี้จะไม่รัน collectstatic อีก)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "cashcrm_project.wsgi:application", "--workers", "2", "--bind", "0.0.0.0:8000"]



