# --- Builder stage ---
FROM python:3.10-slim AS builder
WORKDIR /app

# ติดตั้ง dependencies สำหรับ build
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# สร้าง virtualenv และติดตั้ง Python packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# คัดลอก source code เข้าไป
COPY . .

# รัน collectstatic ใน builder stage
RUN python manage.py collectstatic --noinput

# --- Final (runtime) stage ---
FROM python:3.10-slim AS runtime
WORKDIR /app

# ติดตั้ง runtime library
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/*

# นำ venv จาก builder มาต่อ
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# นำ source code & static files จาก builder มาต่อ
COPY --from=builder /app /app

# คัดลอก entrypoint script แล้วให้เป็น executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ให้ container เริ่มที่ entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# เปิดพอร์ต
EXPOSE 8000

# คำสั่ง default (จะถูก exec ต่อท้ายใน entrypoint.sh ด้วย exec "$@")
CMD ["gunicorn", "cashcrm_project.wsgi:application", "--workers", "2", "--bind", "0.0.0.0:8000"]

