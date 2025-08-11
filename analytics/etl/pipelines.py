import pandas as pd
import requests
from pathlib import Path
from datetime import date, datetime
from django.db import transaction
from django.conf import settings
from analytics.models import BudgetPlan, BudgetActual, RemainingSnapshot

CURRENT_YEAR = date.today().year  # 2025 ตอนนี้

API_PSL_RECORDS_URL = "https://mm9.ith.co.th/api/psl-records/"
FIXED_TOKEN         = "P97LqSVCtNYcJ2RJP8Tp5n8Z4z3pASAPbin6sWjP4a80548a"

class MissingAmountError(ValueError):
    pass

# ------------------------
# 1) Budget Plan (Excel)
# ------------------------
def load_budget_plan_from_excel(xlsx_path: Path) -> int:
    xls = pd.ExcelFile(xlsx_path)
    total = 0
    with transaction.atomic():
        # เคลียร์ตาราง (หรือจะ upsert รายปีได้ ถ้าต้องการ)
        BudgetPlan.objects.all().delete()

        for sheet in xls.sheet_names:
            df = pd.read_excel(xlsx_path, sheet_name=sheet)
            df.columns = [str(c).strip() for c in df.columns]
            req = ["budget_code","description","budget_amount","budget_year"]
            if not all(c in df.columns for c in req):
                raise ValueError(f"Sheet {sheet}: missing required columns {req}")

            df["budget_year"]   = pd.to_numeric(df["budget_year"], errors="coerce")
            df["budget_amount"] = pd.to_numeric(df["budget_amount"], errors="coerce").fillna(0.0)

            rows = []
            for _, r in df.iterrows():
                rows.append(BudgetPlan(
                    budget_year   = int(r.get("budget_year")),
                    budget_code   = str(r.get("budget_code")).strip(),
                    description   = str(r.get("description") or "").strip(),
                    budget_amount = round(float(r.get("budget_amount", 0) or 0), 2),
                    budget_group  = str(r.get("budget_group") or ""),
                    budget_subgroup = str(r.get("budget_subgroup") or ""),
                    budget_type   = str(r.get("budget_type") or ""),
                    budget_owner  = str(r.get("budget_owner") or ""),
                    dept          = str(r.get("Dept") or ""),
                    ro_order      = str(r.get("ro_order") or ""),
                ))
            BudgetPlan.objects.bulk_create(rows, batch_size=1000)
            total += len(rows)
    return total

# ------------------------
# 2) Actuals จาก CSV
# ------------------------
def load_actuals_from_csv(csv_path: Path) -> int:
    try:
        df = pd.read_csv(csv_path)
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="cp874")
    df.columns = [str(c).strip() for c in df.columns]

    if "budget_code" not in df.columns:
        raise ValueError("Actual_old.csv ต้องมีคอลัมน์ budget_code")

    # เลือกวัน: doc_date → po_date → pr_date
    for cand in ["doc_date","po_date","pr_date"]:
        if cand in df.columns:
            df[cand] = pd.to_datetime(df[cand], errors="coerce")
    if "doc_date" not in df.columns:
        df["doc_date"] = pd.NaT
    df["doc_date"] = df["doc_date"].fillna(df.get("po_date")).fillna(df.get("pr_date"))
    df = df[df["doc_date"].notna()]
    df = df[(df["doc_date"] >= "2023-01-01") & (df["doc_date"] <= "2025-04-30")]

    # amount: ใช้ amount ตรงๆ หรือคำนวณจาก unit_cost*quantity
    has_amount = "amount" in df.columns
    has_unit_cost_qty = ("unit_cost" in df.columns) and ("quantity" in df.columns)

    if not has_amount and not has_unit_cost_qty:
        raise MissingAmountError("CSV ไม่มี amount และไม่มี unit_cost/quantity ให้คำนวณ")

    if has_amount:
        amt = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    else:
        amt = pd.to_numeric(df["unit_cost"], errors="coerce").fillna(0.0) * \
              pd.to_numeric(df["quantity"],  errors="coerce").fillna(0.0)

    df_out = pd.DataFrame({
        "doc_date":   pd.to_datetime(df["doc_date"], errors="coerce"),
        "budget_code": df["budget_code"].astype(str).str.strip(),
        "amount":      amt,
    })

    # เขียนด้วย ORM
    rows = [
        BudgetActual(
            doc_date = d.doc_date.date(),
            budget_code = d.budget_code,
            amount = round(float(d.amount or 0), 2),
            source = "csv",
            load_batch_id = f"csv_{datetime.now():%Y%m%d%H%M%S}"
        )
        for d in df_out.itertuples(index=False)
    ]
    with transaction.atomic():
        BudgetActual.objects.bulk_create(rows, batch_size=2000)
    return len(rows)

# ------------------------
# 3) Actuals จาก API (≥ 2025-05-01)
# ------------------------
def load_actuals_from_api_since(start_date="2025-05-01") -> int:
    headers = {"Authorization": f"Bearer {FIXED_TOKEN}"}
    resp = requests.get(API_PSL_RECORDS_URL, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data)
    if df.empty:
        return 0
    df.columns = [str(c).strip() for c in df.columns]

    # แผน mapping ตามไฟล์ dataapi.csv
    # - วันที่: 'date' → doc_date
    # - budget_code: มีตรงตัว
    # - amount: อาจไม่มี → ถ้าไม่มีและไม่มี unit_cost/quantity จะ raise ผิดพลาด
    if "doc_date" not in df.columns:
        if "date" in df.columns:
            df = df.rename(columns={"date": "doc_date"})
        elif "updated_at" in df.columns:
            df = df.rename(columns={"updated_at": "doc_date"})

    required_base = ["budget_code", "doc_date"]
    if not all(c in df.columns for c in required_base):
        raise ValueError(f"API dataset ต้องมี {required_base}")

    amount_col = None
    for c in df.columns:
        if c.lower() in ["amount","total_amount","net_amount","sum_amount","value","price","cost"]:
            amount_col = c; break
    if amount_col is None and "unit_cost" in df.columns and "quantity" in df.columns:
        df["__amount__"] = pd.to_numeric(df["unit_cost"], errors="coerce").fillna(0.0) * \
                           pd.to_numeric(df["quantity"],  errors="coerce").fillna(0.0)
        amount_col = "__amount__"

    if amount_col is None:
        raise MissingAmountError(
            "API ไม่มี amount และไม่มี unit_cost/quantity สำหรับคำนวณยอดใช้จริง — "
            "กรุณาเพิ่มฟิลด์ยอดเงินหรือ endpoint ประกอบ"
        )

    df["doc_date"] = pd.to_datetime(df["doc_date"], errors="coerce")
    df = df[df["doc_date"].notna()]
    df = df[df["doc_date"] >= pd.to_datetime(start_date)]

    df_out = pd.DataFrame({
        "doc_date":   pd.to_datetime(df["doc_date"], errors="coerce"),
        "budget_code": df["budget_code"].astype(str).str.strip(),
        "amount":      pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0),
    })

    rows = [
        BudgetActual(
            doc_date = d.doc_date.date(),
            budget_code = d.budget_code,
            amount = round(float(d.amount or 0), 2),
            source = "api",
            load_batch_id = f"api_{datetime.now():%Y%m%d%H%M%S}"
        )
        for d in df_out.itertuples(index=False)
    ]
    with transaction.atomic():
        BudgetActual.objects.bulk_create(rows, batch_size=2000)
    return len(rows)

# ------------------------
# 4) ทำสรุปคงเหลือ (materialized table)
# ------------------------
def refresh_remaining_snapshot(as_of: date | None = None, year: int | None = None) -> int:
    from django.db.models import Sum
    if as_of is None:
        as_of = date.today()
    if year is None:
        year = as_of.year

    # ดึง Budget ของปีนั้นทั้งหมด
    plans = BudgetPlan.objects.filter(budget_year=year).values(
        "budget_code","description","budget_amount","budget_year"
    )

    # รวม actual ถึง as_of ของปีเดียวกัน
    actuals = (BudgetActual.objects
               .filter(doc_date__year=year, doc_date__lte=as_of)
               .values("budget_code")
               .annotate(actual_to_date=Sum("amount")))

    actual_map = {a["budget_code"]: float(a["actual_to_date"] or 0) for a in actuals}

    # เคลียร์ snapshot เก่าของปีนี้
    RemainingSnapshot.objects.filter(budget_year=year).delete()

    rows = []
    for p in plans:
        used = actual_map.get(p["budget_code"], 0.0)
        budget_amt = float(p["budget_amount"] or 0)
        remaining  = budget_amt - used
        usage_pct  = (used / budget_amt) if budget_amt else None
        rows.append(RemainingSnapshot(
            budget_year   = year,
            budget_code   = p["budget_code"],
            description   = p["description"],
            budget_amount = round(budget_amt, 2),
            actual_to_date= round(used, 2),
            remaining     = round(remaining, 2),
            usage_pct     = round(usage_pct, 4) if usage_pct is not None else None,
        ))

    with transaction.atomic():
        RemainingSnapshot.objects.bulk_create(rows, batch_size=2000)
    return len(rows)
