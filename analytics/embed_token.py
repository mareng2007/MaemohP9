import os, time, jwt


def mint_guest_token(dashboard_id: str, username: str = "embedded_user"):
    secret = os.environ.get("GUEST_TOKEN_JWT_SECRET", "change-me")
    exp = int(time.time()) + 5 * 60
    allowed_domains = os.environ.get("APP_EMBED_HOSTS", "").split() or ["http://localhost:8000"]

    payload = {
        "user": {"username": username, "first_name": "Embedded", "last_name": "User"},
        "resources": [{"type": "dashboard", "id": dashboard_id}],
        "rls": [],
        "domains": allowed_domains,   # 👈 เพิ่มบรรทัดนี้
        "exp": exp,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


