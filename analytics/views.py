from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from analytics.tasks import etl_budget_all

@require_http_methods(["GET","POST"])
def control_panel(request):
    if request.method == "POST":
        etl_budget_all.delay()  # ยิง Celery
        messages.success(request, "สั่งรัน ETL แล้ว โปรดรีเฟรช Dashboard ผ่าน Superset ในอีกสักครู่")
        return redirect("analytics:control_panel")
    return render(request, "analytics/control_panel.html", {
        "superset_url": settings.SUPERSET_PUBLIC_DASHBOARD_URL
    })

