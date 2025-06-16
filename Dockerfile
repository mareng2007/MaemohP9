# ใช้ Python slim image
FROM python:3.10-slim
# FROM python:3.8-slim

# ตั้ง working dir
WORKDIR /code

# ติดตั้ง OS dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# ติดตั้ง Python dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# copy source code
COPY . /code/

# สร้างโฟลเดอร์ static & media
RUN mkdir -p /vol/web/static /vol/web/media

# Default command (Prod)
CMD ["gunicorn", "cashcrm_project.wsgi:application", "--bind", "0.0.0.0:8000"]
