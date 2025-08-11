from celery import shared_task
from django.conf import settings
from pathlib import Path
from analytics.etl.pipelines import (
    load_budget_plan_from_excel,
    load_actuals_from_csv,
    load_actuals_from_api_since,
    refresh_remaining_snapshot,
)

@shared_task(name="analytics.tasks.etl_budget_all")
def etl_budget_all():
    budget_path = Path(settings.DATA_ROOT) / "raw" / "Budget.xlsx"
    actual_csv  = Path(settings.DATA_ROOT) / "raw" / "Actual_old.csv"

    # 1) แผนงบ (ทุกปีในไฟล์)
    load_budget_plan_from_excel(budget_path)

    # 2) ยอดใช้ (CSV: 2023..Apr’25)
    load_actuals_from_csv(actual_csv)

    # 3) ยอดใช้ (API: May’25..วันนี้) — ถ้า API ยังไม่มี amount จะ raise ชัดเจน
    load_actuals_from_api_since("2025-05-01")

    # 4) สร้างสรุปคงเหลือ (ปีปัจจุบัน)
    refresh_remaining_snapshot()

@shared_task(name="analytics.tasks.notify_budget_status")
def notify_budget_status(top_n=10):
    # ใช้ RemainingSnapshot ล่าสุด
    from analytics.notify import fetch_top_usage, format_message, push_line_message
    df = fetch_top_usage(top_n)
    text = format_message(df, title="แจ้งเตือนงบประมาณ (Top ใช้งานสูงสุด)")
    push_line_message(text)
