import logging
from celery import shared_task
from django.conf import settings
from pathlib import Path
from datetime import date, timedelta

from analytics.etl.pipelines import (
    load_budget_plan_from_excel,
    load_actuals_from_csv,
    load_actuals_from_api_since,
    load_actuals_from_api_full_refresh,   # ← เปลี่ยน import มาตัวใหม่
    refresh_remaining_snapshot,
    MissingAmountError,
)

logger = logging.getLogger(__name__)


def _data_root() -> Path:
    base = getattr(settings, "DATA_ROOT", None)
    if not base:
        base = Path(getattr(settings, "BASE_DIR")) / "data"
    return Path(base)


# @shared_task(bind=True, name="analytics.tasks.etl_budget_all")
# def etl_budget_all(self):
#     """
#     Full ETL:
#     - Budget.xlsx: หลายปีหลาย sheet
#     - CSV: ตัดแถว budget_code ที่ไม่สมบูรณ์, รวมหลายปี, ใช้ created_at เป็น timeline ถ้ามี
#     - API: ปี 2025+ เขียน RoIndex เสมอ; เขียน BudgetActual เฉพาะที่มี amount
#     - Refresh RemainingSnapshot
#     """
#     data_root = _data_root() / "raw"
#     data_root.mkdir(parents=True, exist_ok=True)

#     budget_path = data_root / "Budget.xlsx"
#     actual_csv  = data_root / "Actual_old.csv"

#     if not budget_path.exists():
#         raise FileNotFoundError(f"ไม่พบ Budget.xlsx ที่ {budget_path}")
#     if not actual_csv.exists():
#         raise FileNotFoundError(f"ไม่พบ Actual_old.csv ที่ {actual_csv}")

#     logger.info("ETL start: budget=%s actual=%s", budget_path, actual_csv)

#     # 1) Budget
#     n_budget = load_budget_plan_from_excel(budget_path)
#     logger.info("Loaded budget rows: %s", n_budget)

#     # 2) CSV
#     n_csv, max_2025_date = load_actuals_from_csv(
#         actual_csv, start_date="2023-01-01", end_date=str(date.today())
#     )
#     logger.info("Loaded CSV actual rows: %s; max_2025_date=%s", n_csv, max_2025_date)

#     # 3) API (2025+), start after the last CSV 2025 date
#     api_start = date(2025, 1, 1)
#     if max_2025_date:
#         api_start = max(max_2025_date + timedelta(days=1), api_start)

#     # NOTES: ฟังก์ชันใหม่จะไม่ throw ถ้าไม่มี amount — จะคืนจำนวนแถวที่เขียนเข้า BudgetActual
#     n_api = 0
#     try:
#         n_api = load_actuals_from_api_since(api_start.isoformat())
#         logger.info("Loaded API actual rows: %s (since %s)", n_api, api_start)
#     except MissingAmountError as e:
#         logger.warning("Skip API stage: %s", e)
#     except Exception as e:
#         logger.exception("API stage failed (non-fatal): %s", e)

#     # 4) Snapshot
#     n_snap = refresh_remaining_snapshot()
#     logger.info("Refreshed RemainingSnapshot rows: %s", n_snap)

#     return {
#         "budget": n_budget,
#         "csv": n_csv,
#         "api": n_api,
#         "snapshot": n_snap,
#         "api_start": api_start.isoformat(),
#     }


@shared_task(bind=True, name="analytics.tasks.etl_budget_all")
def etl_budget_all(self):
    """
    Full ETL:
    - Budget.xlsx: หลายปีหลาย sheet
    - CSV: ตัดแถว budget_code ที่ไม่สมบูรณ์, รวมหลายปี, ใช้ created_at เป็น timeline ถ้ามี
    - API: **FULL REFRESH** (ลบข้อมูลเก่าที่มาจาก API แล้วโหลดใหม่ทั้งหมด)
    - Refresh RemainingSnapshot
    """
    data_root = _data_root() / "raw"
    data_root.mkdir(parents=True, exist_ok=True)

    budget_path = data_root / "Budget.xlsx"
    actual_csv  = data_root / "Actual_old.csv"

    if not budget_path.exists():
        raise FileNotFoundError(f"ไม่พบ Budget.xlsx ที่ {budget_path}")
    if not actual_csv.exists():
        raise FileNotFoundError(f"ไม่พบ Actual_old.csv ที่ {actual_csv}")

    logger.info("ETL start: budget=%s actual=%s", budget_path, actual_csv)

    # 1) Budget
    n_budget = load_budget_plan_from_excel(budget_path)
    logger.info("Loaded budget rows: %s", n_budget)

    # 2) CSV (ช่วงเวลาเดิม)
    n_csv, _ = load_actuals_from_csv(
        actual_csv, start_date="2023-01-01", end_date=str(date.today())
    )
    logger.info("Loaded CSV actual rows: %s", n_csv)

    # 3) API (FULL REFRESH)
    n_api = 0
    try:
        n_api = load_actuals_from_api_full_refresh()
        logger.info("Loaded API actual rows (FULL REFRESH): %s", n_api)
    except MissingAmountError as e:
        logger.warning("Skip API stage: %s", e)
    except Exception as e:
        logger.exception("API stage failed (non-fatal): %s", e)

    # 4) Snapshot
    n_snap = refresh_remaining_snapshot()
    logger.info("Refreshed RemainingSnapshot rows: %s", n_snap)

    return {
        "budget": n_budget,
        "csv": n_csv,
        "api": n_api,
        "snapshot": n_snap,
        "api_mode": "full_refresh",
    }


@shared_task(name="analytics.tasks.notify_budget_status")
def notify_budget_status(top_n=10):
    from analytics.notify import fetch_top_usage, format_message, push_line_message
    df = fetch_top_usage(top_n)
    text = format_message(df, title="แจ้งเตือนงบประมาณ (Top ใช้งานสูงสุด)")
    push_line_message(text)
    return {"sent_to": len(getattr(settings, "LINE_TARGET_IDS", []))}


