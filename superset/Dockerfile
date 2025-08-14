# /home/mareng2007/django/MaemohP9/superset/Dockerfile
FROM apache/superset:4.1.3

# ติดตั้งไดรเวอร์ Postgres ให้ชัวร์ (แก้ error psycopg2 not found)
USER root
# RUN pip install --no-cache-dir psycopg2-binary==2.9.9 psycopg==3.2.3
RUN pip install --no-cache-dir psycopg2-binary==2.9.9
USER superset
