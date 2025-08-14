from celery import shared_task
from django.conf import settings
from pathlib import Path
from datetime import date
from analytics.etl.pipelines import (
    load_budget_plan_from_excel, load_actuals_from_csv,
    load_actuals_from_api_since, refresh_remaining_snapshot,
)

@shared_task(name="analytics.tasks.etl_budget_all")
def etl_budget_all():
    data_root = Path(settings.DATA_ROOT) / "raw"
    data_root.mkdir(parents=True, exist_ok=True)

    budget_path = data_root / "Budget.xlsx"
    actual_csv  = data_root / "Actual_old.csv"

    load_budget_plan_from_excel(budget_path)
    load_actuals_from_csv(actual_csv, start_date="2023-01-01", end_date=str(date.today()))
    load_actuals_from_api_since("2025-05-01")
    refresh_remaining_snapshot()

@shared_task(name="analytics.tasks.notify_budget_status")
def notify_budget_status(top_n=10):
    from analytics.notify import fetch_top_usage, format_message, push_line_message
    df = fetch_top_usage(top_n)
    text = format_message(df, title="แจ้งเตือนงบประมาณ (Top ใช้งานสูงสุด)")
    push_line_message(text)

