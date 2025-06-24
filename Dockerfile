# --- Builder stage ---
# ใช้ Python slim image
FROM python:3.10-slim AS builder
# FROM python:3.8-slim

# ตั้ง working dir
# WORKDIR /code
WORKDIR /app

# ติดตั้ง OS dependencies
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libpq-dev \
#  && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง Python dependencies
# COPY requirements.txt /code/
# RUN pip install --upgrade pip \
#  && pip install -r requirements.txt

# สร้าง venv และติดตั้ง Python packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# คัดลอก source code ทั้งหมด
# COPY . /code/
COPY . .


# สร้างไฟล์ migrations สำหรับทุกแอป (แม้จะไม่ commit ลง Git ก็จะถูกสร้างที่นี่)
RUN python manage.py makemigrations --noinput


# # สร้างโฟลเดอร์ static & media
# RUN mkdir -p /vol/web/static /vol/web/media

# Collect static (optional, will be copied to final)
RUN python manage.py collectstatic --noinput

# # Default command (Prod)
# CMD ["gunicorn", "cashcrm_project.wsgi:application", "--bind", "0.0.0.0:8000"]


# --- Final stage ---
FROM python:3.10-slim AS runtime
WORKDIR /app

# ติดตั้งแค่ไลบรารี runtime ของ libpq
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/*

# copy venv และ source จาก builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
ENV PATH="/opt/venv/bin:$PATH"

# นำ entrypoint เข้ามาใน image
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


# expose port
EXPOSE 8000

# ให้ entrypoint.sh เป็นจุดเริ่มต้น แล้วตามด้วยคำสั่ง gunicorn
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "cashcrm_project.wsgi:application", "--workers", "2", "--bind", "0.0.0.0:8000"]
