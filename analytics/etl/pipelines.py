from pathlib import Path
from datetime import date, datetime
from django.db import transaction
from django.conf import settings
from analytics.models import BudgetPlan, BudgetActual, RemainingSnapshot

from decimal import Decimal, ROUND_HALF_UP

def _to_decimal(x, q="0.01"):
    return Decimal(str(x or 0)).quantize(Decimal(q), rounding=ROUND_HALF_UP)

class MissingAmountError(ValueError):
    pass

# ------------------------
# 1) Budget Plan (Excel)
# ------------------------
def load_budget_plan_from_excel(xlsx_path: Path) -> int:
    import pandas as pd
    xls = pd.ExcelFile(xlsx_path)
    total = 0
    with transaction.atomic():
        BudgetPlan.objects.all().delete()
        for sheet in xls.sheet_names:
            df = pd.read_excel(xlsx_path, sheet_name=sheet)
            df.columns = [str(c).strip() for c in df.columns]
            req = ["budget_code", "description", "budget_amount", "budget_year"]
            if not all(c in df.columns for c in req):
                raise ValueError(f"Sheet {sheet}: missing required columns {req}")

            df["budget_year"] = pd.to_numeric(df["budget_year"], errors="coerce")
            df["budget_amount"] = pd.to_numeric(df["budget_amount"], errors="coerce").fillna(0.0)
            df = df.dropna(subset=["budget_year"])  # 👈 กัน NaN

            rows = []
            for _, r in df.iterrows():
                rows.append(BudgetPlan(
                    budget_year=int(r["budget_year"]),
                    budget_code=str(r.get("budget_code", "")).strip(),
                    description=str(r.get("description", "")).strip(),
                    budget_amount=_to_decimal(r.get("budget_amount", 0)),
                    budget_group=str(r.get("budget_group") or ""),
                    budget_subgroup=str(r.get("budget_subgroup") or ""),
                    budget_type=str(r.get("budget_type") or ""),
                    budget_owner=str(r.get("budget_owner") or ""),
                    dept=str(r.get("Dept") or ""),
                    ro_order=str(r.get("ro_order") or ""),
                ))
            BudgetPlan.objects.bulk_create(rows, batch_size=1000)
            total += len(rows)
    return total

# ------------------------
# 2) Actuals จาก CSV
# ------------------------
def load_actuals_from_csv(csv_path: Path, start_date=None, end_date=None) -> int:
    import pandas as pd
    try:
        df = pd.read_csv(csv_path)
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="cp874")
    df.columns = [str(c).strip() for c in df.columns]
    if "budget_code" not in df.columns:
        raise ValueError("Actual_old.csv ต้องมีคอลัมน์ budget_code")

    for cand in ["doc_date", "po_date", "pr_date"]:
        if cand in df.columns:
            df[cand] = pd.to_datetime(df[cand], errors="coerce")
    if "doc_date" not in df.columns:
        df["doc_date"] = pd.NaT
    df["doc_date"] = df["doc_date"].fillna(df.get("po_date")).fillna(df.get("pr_date"))
    df = df[df["doc_date"].notna()]

    if start_date:
        df = df[df["doc_date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["doc_date"] <= pd.to_datetime(end_date)]

    has_amount = "amount" in df.columns
    has_uc_q = ("unit_cost" in df.columns) and ("quantity" in df.columns)
    if not has_amount and not has_uc_q:
        raise MissingAmountError("CSV ไม่มี amount และไม่มี unit_cost/quantity ให้คำนวณ")

    amt = (
        pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        if has_amount else
        pd.to_numeric(df["unit_cost"], errors="coerce").fillna(0.0)
        * pd.to_numeric(df["quantity"], errors="coerce").fillna(0.0)
    )

    df_out = pd.DataFrame({
        "doc_date": pd.to_datetime(df["doc_date"], errors="coerce"),
        "budget_code": df["budget_code"].astype(str).str.strip(),
        "amount": amt,
    })

    rows = [BudgetActual(
        doc_date=d.doc_date.date(),
        budget_code=d.budget_code,
        amount=_to_decimal(d.amount),
        source="csv",
        load_batch_id=f"csv_{datetime.now():%Y%m%d%H%M%S}",
    ) for d in df_out.itertuples(index=False)]

    with transaction.atomic():
        BudgetActual.objects.bulk_create(rows, batch_size=2000)
    return len(rows)

# ------------------------
# 3) Actuals จาก API (≥ 2025-05-01)
# ------------------------
def load_actuals_from_api_since(start_date="2025-05-01") -> int:
    import pandas as pd, requests
    api_url = settings.API_PSL_RECORDS_URL
    token = settings.API_FIXED_TOKEN
    if not api_url:
        return 0
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.get(api_url, headers=headers, timeout=60)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    if df.empty:
        return 0
    df.columns = [str(c).strip() for c in df.columns]

    if "doc_date" not in df.columns:
        if "date" in df.columns:
            df = df.rename(columns={"date": "doc_date"})
        elif "updated_at" in df.columns:
            df = df.rename(columns={"updated_at": "doc_date"})

    required = ["budget_code", "doc_date"]
    if not all(c in df.columns for c in required):
        raise ValueError(f"API dataset ต้องมี {required}")

    amount_col = next(
        (c for c in df.columns if c.lower() in
         ["amount", "total_amount", "net_amount", "sum_amount", "value", "price", "cost"]),
        None
    )
    if amount_col is None and {"unit_cost", "quantity"}.issubset(df.columns):
        df["__amount__"] = (
            pd.to_numeric(df["unit_cost"], errors="coerce").fillna(0.0)
            * pd.to_numeric(df["quantity"], errors="coerce").fillna(0.0)
        )
        amount_col = "__amount__"
    if amount_col is None:
        raise MissingAmountError("API ไม่มี amount และไม่มี unit_cost/quantity สำหรับคำนวณยอดใช้จริง")

    df["doc_date"] = pd.to_datetime(df["doc_date"], errors="coerce")
    df = df[df["doc_date"].notna() & (df["doc_date"] >= pd.to_datetime(start_date))]

    df_out = pd.DataFrame({
        "doc_date": pd.to_datetime(df["doc_date"], errors="coerce"),
        "budget_code": df["budget_code"].astype(str).str.strip(),
        "amount": pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0),
    })

    rows = [BudgetActual(
        doc_date=d.doc_date.date(),
        budget_code=d.budget_code,
        amount=_to_decimal(d.amount),  # <<< ใช้ Decimal ให้สม่ำเสมอ
        source="api",
        load_batch_id=f"api_{datetime.now():%Y%m%d%H%M%S}",
    ) for d in df_out.itertuples(index=False)]

    with transaction.atomic():
        BudgetActual.objects.bulk_create(rows, batch_size=2000)
    return len(rows)

# ------------------------
# 4) Remaining Snapshot
# ------------------------
def refresh_remaining_snapshot(as_of: date | None = None, year: int | None = None) -> int:
    from django.db.models import Sum
    if as_of is None:
        as_of = date.today()
    if year is None:
        year = as_of.year

    plans = (
        BudgetPlan.objects.filter(budget_year=year)
        .values("budget_code", "description", "budget_amount", "budget_owner", "budget_group")
    )
    actuals = (
        BudgetActual.objects
        .filter(doc_date__year=year, doc_date__lte=as_of)
        .values("budget_code").annotate(actual_to_date=Sum("amount"))
    )
    actual_map = {a["budget_code"]: float(a["actual_to_date"] or 0) for a in actuals}

    RemainingSnapshot.objects.filter(budget_year=year).delete()

    rows = []
    for p in plans:
        used = actual_map.get(p["budget_code"], 0.0)
        budget_amt = float(p["budget_amount"] or 0)
        remaining = budget_amt - used
        usage_pct = (used / budget_amt) if budget_amt else None
        rows.append(RemainingSnapshot(
            budget_year=year,
            budget_code=p["budget_code"],
            description=p["description"] or "",
            budget_amount=round(budget_amt, 2),
            actual_to_date=round(used, 2),
            remaining=round(remaining, 2),
            usage_pct=round(usage_pct, 4) if usage_pct is not None else None,
            budget_owner=p.get("budget_owner") or "",
            budget_group=p.get("budget_group") or "",
        ))
    with transaction.atomic():
        RemainingSnapshot.objects.bulk_create(rows, batch_size=2000)
    return len(rows)


