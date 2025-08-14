import os
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods, require_GET
from django.contrib.auth.decorators import login_required  # 👈 เพิ่ม import
from analytics.tasks import etl_budget_all
from analytics.models import RemainingSnapshot
from .embed_token import mint_guest_token

@require_http_methods(["GET","POST"])
def control_panel(request):
    if request.method == "POST":
        etl_budget_all.delay()
        messages.success(request, "สั่งรัน ETL แล้ว! โปรดรีเฟรช Dashboard ในอีกสักครู่")
        return redirect("analytics:control_panel")

    latest = (RemainingSnapshot.objects
              .order_by("-snapshot_at")
              .values("snapshot_at","budget_year")
              .first())
    return render(request, "analytics/control_panel.html", {
        "superset_url": os.getenv("SUPERSET_BASE_URL", settings.SUPERSET_BASE_URL),
        "latest": latest,
    })


def embed_dashboard(request):
    return render(request, "analytics/embed_dashboard.html", {
        "superset_url": os.getenv("SUPERSET_BASE_URL", settings.SUPERSET_BASE_URL),
        "dash_id": os.getenv("SUPERSET_EMBED_DASHBOARD_ID", settings.SUPERSET_EMBED_DASHBOARD_ID or "")
    })


@require_GET
@login_required  # 👈 บังคับให้ต้องล็อกอินก่อนถึงจะขอ token ได้
def superset_guest_token(request):
    dash_id = os.getenv("SUPERSET_EMBED_DASHBOARD_ID", settings.SUPERSET_EMBED_DASHBOARD_ID or "")
    if not dash_id:
        return HttpResponseBadRequest("Missing SUPERSET_EMBED_DASHBOARD_ID")
    username = request.user.username if getattr(request, "user", None) and request.user.is_authenticated else "guest"
    token = mint_guest_token(dash_id, username=username)
    return JsonResponse({"token": token})




