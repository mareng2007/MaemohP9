from django.urls import path
from .views import control_panel, embed_dashboard, superset_guest_token, line_webhook, line_debug, debug_api_latest

app_name = "analytics"
urlpatterns = [
    path("control/", control_panel, name="control_panel"),
    path("embed/", embed_dashboard, name="embed"),
    path("api/superset_token/", superset_guest_token, name="superset_token"),
    path("line/webhook/", line_webhook, name="line_webhook"),

    # 👇 DEV only
    # โหมดทดสอบผ่านเว็บ (ไม่ต้องมีลายเซ็นจาก LINE)
    path("line/debug/", line_debug, name="line_debug"),
    path("debug/api-latest/", debug_api_latest, name="debug_api_latest"),
]



