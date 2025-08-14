import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me")
SQLALCHEMY_DATABASE_URI = os.environ.get("SUPERSET_DATABASE_URI")

FEATURE_FLAGS = { "EMBEDDED_SUPERSET": True }

# ==== Mode switch (dev/prod) ====
# ใช้ตัวแปรนี้เป็นตัวกำหนด (ตั้ง SUPERSET_ENV=production ใน prod)
SUPERSET_ENV = os.environ.get("SUPERSET_ENV", "development").lower()
IS_PROD = SUPERSET_ENV in ("prod", "production")

# ==== Guest Token ====
GUEST_ROLE_NAME = os.environ.get("GUEST_ROLE_NAME", "Gamma")
GUEST_TOKEN_JWT_SECRET = os.environ.get("GUEST_TOKEN_JWT_SECRET", "change-me")
GUEST_TOKEN_JWT_ALGO = "HS256"

# ==== Embedding origins ====
if IS_PROD:
    default_hosts = "https://mining.utrizd.com"
else:
    default_hosts = "http://localhost:8000 http://127.0.0.1:8000"

APP_EMBED_HOSTS = os.environ.get("APP_EMBED_HOSTS", default_hosts).split()

# ==== CSP / Talisman ====
# Prod: เข้ม, Dev: ผ่อน
TALISMAN_ENABLED = IS_PROD
CONTENT_SECURITY_POLICY_WARNING = False

# ทางเลือก: ถ้าต้องการกำหนด CSP เอง (โดยไม่พึ่ง Talisman) เปิดบล็อกนี้
# - แนะนำเปิดเฉพาะตอน DEV เพื่อ debug ง่าย
USE_MANUAL_CSP = not IS_PROD  # Dev ใช้เอง, Prod ให้ Talisman จัดการ

if USE_MANUAL_CSP:
    # สร้าง CSP frame-ancestors จาก APP_EMBED_HOSTS
    _fa = " ".join(APP_EMBED_HOSTS)
    OVERRIDE_HTTP_HEADERS = {
        "Content-Security-Policy": f"frame-ancestors 'self' {_fa}",
        # "X-Frame-Options": "ALLOW-FROM https://mining.utrizd.com",  # ไม่จำเป็นถ้าใช้ CSP สมัยใหม่
    }
