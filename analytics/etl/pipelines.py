from pathlib import Path
from datetime import date, datetime, time as dtime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import os  # 👈 เพิ่ม
from django.db import transaction
from django.conf import settings
from django.utils import timezone as tz

from analytics.models import BudgetPlan, BudgetActual, RemainingSnapshot, RoIndex


# ------------- Decimal helpers -------------
def _to_decimal(x, q="0.01"):
    try:
        return Decimal(str(x if x is not None else 0)).quantize(Decimal(q), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0").quantize(Decimal(q), rounding=ROUND_HALF_UP)


# ------------- TZ helpers -------------
def _aware(dt: datetime) -> datetime:
    """Force timezone-aware datetime using project's TIME_ZONE."""
    if dt is None:
        return None
    cur_tz = tz.get_current_timezone()
    if tz.is_naive(dt):
        return tz.make_aware(dt, cur_tz)
    return dt.astimezone(cur_tz)


class MissingAmountError(ValueError):
    pass


# ------------- Debug export helpers (dev only) -------------
def _data_root() -> Path:
    base = getattr(settings, "DATA_ROOT", None)
    if not base:
        base = Path(getattr(settings, "BASE_DIR")) / "data"
    return Path(base)

def _debug_export_enabled() -> bool:
    return bool(os.getenv("ANALYTICS_DEBUG_EXPORT_API") == "1" or getattr(settings, "DEBUG", False))

def _debug_export_api_payload(raw_text: str, df_head=None) -> dict | None:
    """
    เซฟไฟล์ดิบจาก API และหัวตาราง normalize (CSV) ไว้ดูเฉพาะตอน dev
    จะสร้างโฟลเดอร์: <DATA_ROOT>/dev_exports/
    """
    if not _debug_export_enabled():
        return None

    outdir = _data_root() / "dev_exports"
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")

    raw_path = outdir / f"api_raw_{ts}.json"
    raw_path.write_text(raw_text or "", encoding="utf-8")

    norm_path = None
    if df_head is not None:
        norm_path = outdir / f"api_norm_{ts}.csv"
        try:
            df_head.to_csv(norm_path, index=False)
        except Exception:
            norm_path = None

    (outdir / "latest.txt").write_text(ts, encoding="utf-8")
    return {"raw": str(raw_path), "norm": (str(norm_path) if norm_path else None), "ts": ts}


# ----------------------------------------------------------------
# Budget Plan (Excel, หลายปีหลาย sheet)
# ----------------------------------------------------------------
def load_budget_plan_from_excel(xlsx_path: Path) -> int:
    import pandas as pd
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Excel not found: {xlsx_path}")

    xls = pd.ExcelFile(xlsx_path)
    total = 0
    with transaction.atomic():
        BudgetPlan.objects.all().delete()
        for sheet in xls.sheet_names:
            df = pd.read_excel(xlsx_path, sheet_name=sheet)
            df.columns = [str(c).strip() for c in df.columns]

            # เดา budget_year จากชื่อ sheet ถ้าไม่มีในคอลัมน์
            if "budget_year" not in df.columns:
                import re
                m = re.search(r"(20\d{2})", sheet)
                if m:
                    df["budget_year"] = int(m.group(1))

            req = ["budget_code", "description", "budget_amount", "budget_year"]
            if not all(c in df.columns for c in req):
                raise ValueError(f"Sheet {sheet}: missing required columns {req}")

            df["budget_year"] = pd.to_numeric(df["budget_year"], errors="coerce")
            df["budget_amount"] = pd.to_numeric(df["budget_amount"], errors="coerce").fillna(0.0)
            df = df.dropna(subset=["budget_year"])

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


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
def _to_date(d):
    if d is None:
        return None
    if isinstance(d, date):
        return d
    return datetime.fromisoformat(str(d)).date()


# ----------------------------------------------------------------
# Actuals จาก CSV (หลายปี, ตัดแถวไม่มี budget_code, ใช้ created_at ถ้ามี)
# ----------------------------------------------------------------
def load_actuals_from_csv(csv_path: Path, start_date=None, end_date=None) -> tuple[int, date | None]:
    import pandas as pd
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="cp874")

    df.columns = [str(c).strip() for c in df.columns]
    if "budget_code" not in df.columns:
        raise ValueError("Actual_old.csv ต้องมีคอลัมน์ budget_code")

    # กรอง budget_code
    valid = ~df["budget_code"].isna()
    df = df[valid].copy()
    df["budget_code"] = df["budget_code"].astype(str).str.strip()
    df = df[~df["budget_code"].isin(["", "nan", "NaN", "None", "NULL", "null"])]

    # mapping วันที่และ created_at
    for cand in ["doc_date", "po_date", "pr_date", "created_at"]:
        if cand in df.columns:
            df[cand] = pd.to_datetime(df[cand], errors="coerce")

    if "doc_date" not in df.columns:
        df["doc_date"] = pd.NaT
    df["doc_date"] = df["doc_date"].fillna(df.get("created_at")).fillna(df.get("po_date")).fillna(df.get("pr_date"))
    df = df[df["doc_date"].notna()]

    if start_date:
        df = df[df["doc_date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["doc_date"] <= pd.to_datetime(end_date)]

    has_amount = "amount" in df.columns
    has_uc_q   = {"unit_cost", "quantity"}.issubset(df.columns)
    if not has_amount and not has_uc_q:
        raise MissingAmountError("CSV ไม่มี amount และไม่มี unit_cost/quantity ให้คำนวณ")

    amt = (
        pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        if has_amount else
        pd.to_numeric(df["unit_cost"], errors="coerce").fillna(0.0) *
        pd.to_numeric(df["quantity"],  errors="coerce").fillna(0.0)
    )

    # event_ts
    event_ts = df.get("created_at")
    no_event_mask = event_ts.isna() if event_ts is not None else None
    if event_ts is None:
        event_ts = df["doc_date"]
    else:
        event_ts = event_ts.copy()
        if no_event_mask is not None and no_event_mask.any():
            fill_index = df[no_event_mask].index
            event_ts.loc[fill_index] = df.loc[fill_index, "doc_date"].apply(lambda d: pd.Timestamp.combine(d.date(), dtime(12, 0)))

    df_out = pd.DataFrame({
        "doc_date": pd.to_datetime(df["doc_date"], errors="coerce"),
        "budget_code": df["budget_code"].astype(str).str.strip(),
        "amount": amt,
        "event_ts": pd.to_datetime(event_ts, errors="coerce"),
        "source_ref": df.get("id", "")
    }).dropna(subset=["doc_date", "event_ts"])

    # หา max ของปี 2025
    df_2025 = df_out[df_out["doc_date"].dt.year == 2025]
    max_2025 = df_2025["doc_date"].max()
    max_2025_date = max_2025.date() if pd.notna(max_2025) else None

    # บันทึก
    with transaction.atomic():
        qs = BudgetActual.objects.filter(source="csv")
        if start_date:
            sd = _to_date(start_date); qs = qs.filter(doc_date__gte=sd)
        if end_date:
            ed = _to_date(end_date);   qs = qs.filter(doc_date__lte=ed)
        qs.delete()

        rows = []
        batch_id = f"csv_{datetime.now():%Y%m%d%H%M%S}"
        seq = 0
        for d in df_out.sort_values(["event_ts","doc_date"]).itertuples(index=False):
            seq += 1
            raw_evt = getattr(d, "event_ts", None)
            if hasattr(raw_evt, "to_pydatetime"):
                raw_evt = raw_evt.to_pydatetime()
            event_aware = _aware(raw_evt) if raw_evt is not None else _aware(datetime.combine(d.doc_date.date(), dtime(12, 0)))
            rows.append(BudgetActual(
                doc_date    = d.doc_date.date(),
                budget_code = d.budget_code,
                amount      = _to_decimal(d.amount),
                source      = "csv",
                load_batch_id = batch_id,
                event_ts    = event_aware,
                source_ref  = str(getattr(d, "source_ref", "") or ""),
                seq_no      = seq,
            ))
        BudgetActual.objects.bulk_create(rows, batch_size=2000)

    return len(rows), max_2025_date


# ----------------------------------------------------------------
# Actuals จาก API (ปี 2025+ พร้อมลำดับเวลา) + อัปเดต RoIndex เสมอ
# ใช้ amount_total ถ้ามีใน header; ถ้าไม่มี → fallback ยิง /{id} รวมยอดจาก items
# ----------------------------------------------------------------
def load_actuals_from_api_since(start_date="2025-01-01") -> int:
    import pandas as pd, requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    api_url = getattr(settings, "API_PSL_RECORDS_URL", "")
    token   = getattr(settings, "API_FIXED_TOKEN", "")
    if not api_url:
        return 0

    # ---- session + retry ----
    sess = requests.Session()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[502,503,504])
    sess.mount("http://",  HTTPAdapter(max_retries=retries))
    sess.mount("https://", HTTPAdapter(max_retries=retries))

    # ---- helper: fetch all pages (DRF-style) ----
    def _fetch_all(u: str) -> pd.DataFrame:
        rows, first_text = [], None
        while u:
            r = sess.get(u, headers=headers, timeout=60)
            r.raise_for_status()
            if first_text is None:
                first_text = r.text or ""
            data = r.json()
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                rows += data["results"]
                u = data.get("next")
            elif isinstance(data, list):
                rows += data
                u = None
            else:
                rows += [data]
                u = None
        # dev export (raw + head)
        try:
            _debug_export_api_payload(first_text or "", pd.DataFrame(rows).head(200) if rows else None)
        except Exception:
            pass
        return pd.DataFrame(rows)

    # ---- get headers (psl-records) ----
    df = _fetch_all(api_url)
    if df.empty:
        return 0
    df.columns = [str(c).strip() for c in df.columns]

    # ---- mappings ----
    budget_col  = getattr(settings, "API_BUDGET_CODE_COLUMN", "budget_code")
    date_col    = getattr(settings, "API_DATE_COLUMN", "") or "date"
    event_col   = getattr(settings, "API_EVENT_TS_COLUMN", "")
    year_col    = getattr(settings, "API_BUDGET_YEAR_COLUMN", "budget_year")
    id_col      = getattr(settings, "API_RO_ID_COLUMN", "id")
    created_col = getattr(settings, "API_CREATED_AT_COLUMN", "created_at")
    amount_col  = getattr(settings, "API_AMOUNT_COLUMN", "amount_total") or "amount_total"

    # ต้องมี id เสมอ
    if id_col not in df.columns:
        raise ValueError(f"API dataset ต้องมีคอลัมน์รหัส RO: {id_col}")

    # ถ้าไม่มี budget_code ใน header → ข้ามสเต็ป API (ตาม requirement)
    if budget_col not in df.columns:
        return 0

    # ---- normalize doc_date ----
    if date_col in df.columns:
        df = df.rename(columns={date_col: "doc_date"})
    elif "doc_date" not in df.columns:
        for cand in ["date", "issued_at", "updated_at", "created_at"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "doc_date"})
                break
    if "doc_date" not in df.columns:
        raise ValueError("API dataset ไม่มีคอลัมน์วันที่ (กำหนด API_DATE_COLUMN ให้ตรง)")

    # ---- clean budget_code + filter by start_date ----
    df[budget_col] = df[budget_col].astype(str).str.strip()
    df = df[~df[budget_col].isin(["", "nan", "NaN", "None", "NULL", "null"])]
    df["doc_date"] = pd.to_datetime(df["doc_date"], errors="coerce")
    df = df[df["doc_date"].notna() & (df["doc_date"] >= pd.to_datetime(start_date))]

    # ---- choose event_ts: created_at > event_col > doc_date ----
    if created_col in df.columns:
        evt = pd.to_datetime(df[created_col], errors="coerce")
    elif event_col and event_col in df.columns:
        evt = pd.to_datetime(df[event_col], errors="coerce")
    else:
        evt = pd.to_datetime(df["doc_date"], errors="coerce")
    df["__evt__"] = evt.fillna(df["doc_date"])

    # ---- derive budget_year if missing ----
    if year_col not in df.columns:
        df[year_col] = None
    df["__year__"] = pd.to_numeric(df[year_col], errors="coerce")
    df["__year__"] = df["__year__"].fillna(df["doc_date"].dt.year).astype(int)

    # ---- dedup header by id (กัน call ซ้ำ/ข้อมูลซ้ำ) ----
    df = df.drop_duplicates(subset=[id_col]).reset_index(drop=True)

    # ========== AMOUNT: fast-path (amount_total) or fallback(detail) ==========
    has_amount = amount_col in df.columns
    if has_amount:
        df["__amt__"] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0)
    else:
        # --- fallback: go per-id and sum items ---
        def _extract_items(detail: dict):
            if not isinstance(detail, dict):
                return []
            if isinstance(detail.get("psl_items"), list):
                return detail["psl_items"]
            for k in ("items", "lines", "details"):
                if isinstance(detail.get(k), list):
                    return detail[k]
            for v in detail.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return v
            return []

        def _item_amount(d: dict) -> float:
            if not isinstance(d, dict):
                return 0.0
            for k in ("psl_items_estimated_price", "estimated_price", "total_price_incl_vat",
                      "line_total", "amount", "total_price"):
                if k in d:
                    try:
                        return float(d[k] or 0)
                    except Exception:
                        pass
            q = p = None
            for k in ("psl_items_qty", "quantity", "qty"):
                if k in d:
                    try: q = float(d[k] or 0); break
                    except Exception: pass
            for k in ("psl_items_unit_price", "unit_price", "price"):
                if k in d:
                    try: p = float(d[k] or 0); break
                    except Exception: pass
            return (q*p) if (q is not None and p is not None) else 0.0

        amount_by_id = {}
        base_detail = api_url.rstrip("/") + "/{id}"
        for rid in df[id_col].astype(str):
            try:
                det = sess.get(base_detail.format(id=rid), headers=headers, timeout=60)
                det.raise_for_status()
                j = det.json()
            except Exception:
                amount_by_id[rid] = 0.0
                continue
            items = _extract_items(j)
            total = 0.0
            for it in items:
                try:
                    total += _item_amount(it)
                except Exception:
                    pass
            amount_by_id[rid] = total
        df["__amt__"] = df[id_col].astype(str).map(amount_by_id).fillna(0.0)

    # ---- prepare frames ----
    ro_df = pd.DataFrame({
        "ro_id":       df[id_col].astype(str),
        "budget_code": df[budget_col].astype(str).str.strip(),
        "budget_year": df["__year__"].astype(int),
        "created_at":  pd.to_datetime(df["__evt__"], errors="coerce"),
        "amount":      df["__amt__"].fillna(0.0),
    })

    out_df = pd.DataFrame({
        "doc_date":    pd.to_datetime(df["doc_date"], errors="coerce"),
        "budget_code": df[budget_col].astype(str).str.strip(),
        "amount":      df["__amt__"].fillna(0.0),
        "event_ts":    pd.to_datetime(df["__evt__"], errors="coerce"),
        "source_ref":  df[id_col].astype(str),
    })
    out_df = out_df[out_df["amount"] > 0]

    # ---- write to DB ----
    start_d = _to_date(start_date)
    with transaction.atomic():
        # RoIndex: เคลียร์ช่วงที่จะเขียนใหม่ก่อน
        RoIndex.objects.filter(created_at__gte=_aware(datetime.combine(start_d, dtime(0,0)))).delete()
        rows = []
        for r in ro_df.itertuples(index=False):
            rows.append(RoIndex(
                ro_id=str(r.ro_id),
                budget_code=str(r.budget_code),
                budget_year=int(r.budget_year),
                created_at=_aware(r.created_at.to_pydatetime() if hasattr(r.created_at, "to_pydatetime") else r.created_at),
                amount=_to_decimal(getattr(r, "amount", 0)),
            ))
        RoIndex.objects.bulk_create(rows, batch_size=2000)

    if out_df.empty:
        return 0

    with transaction.atomic():
        BudgetActual.objects.filter(source="api", doc_date__gte=start_d).delete()
        rows, batch_id, seq = [], f"api_{datetime.now():%Y%m%d%H%M%S}", 0
        for d in out_df.sort_values(["event_ts","doc_date"]).itertuples(index=False):
            seq += 1
            raw_evt = getattr(d, "event_ts", None)
            if hasattr(raw_evt, "to_pydatetime"):
                raw_evt = raw_evt.to_pydatetime()
            event_ts = _aware(raw_evt) if raw_evt is not None else _aware(datetime.combine(d.doc_date.date(), dtime(12,0)))
            rows.append(BudgetActual(
                doc_date      = d.doc_date.date(),
                budget_code   = d.budget_code,
                amount        = _to_decimal(d.amount),
                source        = "api",
                load_batch_id = batch_id,
                event_ts      = event_ts,
                source_ref    = str(getattr(d, "source_ref", "") or ""),
                seq_no        = seq,
            ))
        BudgetActual.objects.bulk_create(rows, batch_size=2000)
    return len(rows)




# ----------------------------------------------------------------
# Actuals จาก API (FULL REFRESH: ไม่สนใจ max_date/ช่วงเวลา)
# ลบ RoIndex ทั้งหมด + ลบ BudgetActual ที่ source="api" ทั้งหมด แล้วเขียนใหม่
# ----------------------------------------------------------------
def load_actuals_from_api_full_refresh() -> int:
    import pandas as pd, requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    api_url = getattr(settings, "API_PSL_RECORDS_URL", "")
    token   = getattr(settings, "API_FIXED_TOKEN", "")
    if not api_url:
        return 0

    # ---- session + retry ----
    sess = requests.Session()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[502,503,504])
    sess.mount("http://",  HTTPAdapter(max_retries=retries))
    sess.mount("https://", HTTPAdapter(max_retries=retries))

    # ---- helper: fetch all pages (DRF-style) ----
    def _fetch_all(u: str) -> pd.DataFrame:
        rows, first_text = [], None
        while u:
            r = sess.get(u, headers=headers, timeout=60)
            r.raise_for_status()
            if first_text is None:
                first_text = r.text or ""
            data = r.json()
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                rows += data["results"]; u = data.get("next")
            elif isinstance(data, list):
                rows += data; u = None
            else:
                rows += [data]; u = None
        # dev export (raw + head)
        try:
            _debug_export_api_payload(first_text or "", pd.DataFrame(rows).head(200) if rows else None)
        except Exception:
            pass
        return pd.DataFrame(rows)

    df = _fetch_all(api_url)
    if df.empty:
        return 0
    df.columns = [str(c).strip() for c in df.columns]

    # ---- mappings ----
    budget_col  = getattr(settings, "API_BUDGET_CODE_COLUMN", "budget_code")
    date_col    = getattr(settings, "API_DATE_COLUMN", "") or "date"
    event_col   = getattr(settings, "API_EVENT_TS_COLUMN", "")
    year_col    = getattr(settings, "API_BUDGET_YEAR_COLUMN", "budget_year")
    id_col      = getattr(settings, "API_RO_ID_COLUMN", "id")
    created_col = getattr(settings, "API_CREATED_AT_COLUMN", "created_at")
    amount_col  = getattr(settings, "API_AMOUNT_COLUMN", "amount_total") or "amount_total"

    if id_col not in df.columns:
        raise ValueError(f"API dataset ต้องมีคอลัมน์รหัส RO: {id_col}")

    # ถ้าไม่มี budget_code → ไม่บันทึก (ตามข้อกำหนดเดิม)
    if budget_col not in df.columns:
        return 0

    # ---- normalize doc_date ----
    if date_col in df.columns:
        df = df.rename(columns={date_col: "doc_date"})
    elif "doc_date" not in df.columns:
        for cand in ["date", "issued_at", "updated_at", "created_at"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "doc_date"})
                break
    if "doc_date" not in df.columns:
        raise ValueError("API dataset ไม่มีคอลัมน์วันที่ (กำหนด API_DATE_COLUMN ให้ตรง)")

    # ---- clean budget_code + ไม่กรองตามวันที่ ----
    df[budget_col] = df[budget_col].astype(str).str.strip()
    df = df[~df[budget_col].isin(["", "nan", "NaN", "None", "NULL", "null"])]
    df["doc_date"] = pd.to_datetime(df["doc_date"], errors="coerce")
    df = df[df["doc_date"].notna()]  # << ไม่มีเงื่อนไข >= start_date แล้ว

    # ---- choose event_ts: created_at > event_col > doc_date ----
    if created_col in df.columns:
        evt = pd.to_datetime(df[created_col], errors="coerce")
    elif event_col and event_col in df.columns:
        evt = pd.to_datetime(df[event_col], errors="coerce")
    else:
        evt = pd.to_datetime(df["doc_date"], errors="coerce")
    df["__evt__"] = evt.fillna(df["doc_date"])

    # ---- derive budget_year if missing ----
    if year_col not in df.columns:
        df[year_col] = None
    df["__year__"] = pd.to_numeric(df[year_col], errors="coerce")
    df["__year__"] = df["__year__"].fillna(df["doc_date"].dt.year).astype(int)

    # ---- dedup header by id ----
    df = df.drop_duplicates(subset=[id_col]).reset_index(drop=True)

    # ========== AMOUNT: fast-path (amount_total) or fallback(detail) ==========
    has_amount = amount_col in df.columns
    if has_amount:
        df["__amt__"] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0)
    else:
        def _extract_items(detail: dict):
            if not isinstance(detail, dict): return []
            if isinstance(detail.get("psl_items"), list): return detail["psl_items"]
            for k in ("items", "lines", "details"):
                if isinstance(detail.get(k), list): return detail[k]
            for v in detail.values():
                if isinstance(v, list) and v and isinstance(v[0], dict): return v
            return []

        def _item_amount(d: dict) -> float:
            if not isinstance(d, dict): return 0.0
            for k in ("psl_items_estimated_price", "estimated_price", "total_price_incl_vat",
                      "line_total", "amount", "total_price"):
                if k in d:
                    try: return float(d[k] or 0)
                    except Exception: pass
            q = p = None
            for k in ("psl_items_qty", "quantity", "qty"):
                if k in d:
                    try: q = float(d[k] or 0); break
                    except Exception: pass
            for k in ("psl_items_unit_price", "unit_price", "price"):
                if k in d:
                    try: p = float(d[k] or 0); break
                    except Exception: pass
            return (q*p) if (q is not None and p is not None) else 0.0

        amount_by_id = {}
        base_detail = api_url.rstrip("/") + "/{id}"
        for rid in df[id_col].astype(str):
            try:
                det = sess.get(base_detail.format(id=rid), headers=headers, timeout=60)
                det.raise_for_status()
                j = det.json()
            except Exception:
                amount_by_id[rid] = 0.0
                continue
            items = _extract_items(j)
            total = 0.0
            for it in items:
                try:
                    total += _item_amount(it)
                except Exception:
                    pass
            amount_by_id[rid] = total
        df["__amt__"] = df[id_col].astype(str).map(amount_by_id).fillna(0.0)

    # ---- prepare frames ----
    ro_df = pd.DataFrame({
        "ro_id":       df[id_col].astype(str),
        "budget_code": df[budget_col].astype(str).str.strip(),
        "budget_year": df["__year__"].astype(int),
        "created_at":  pd.to_datetime(df["__evt__"], errors="coerce"),
        "amount":      df["__amt__"].fillna(0.0),
    })

    out_df = pd.DataFrame({
        "doc_date":    pd.to_datetime(df["doc_date"], errors="coerce"),
        "budget_code": df[budget_col].astype(str).str.strip(),
        "amount":      df["__amt__"].fillna(0.0),
        "event_ts":    pd.to_datetime(df["__evt__"], errors="coerce"),
        "source_ref":  df[id_col].astype(str),
    })
    out_df = out_df[out_df["amount"] > 0]

    # ---- write to DB (FULL refresh สำหรับข้อมูลจาก API) ----
    with transaction.atomic():
        # ล้าง RoIndex ทั้งหมด แล้วเขียนใหม่
        RoIndex.objects.all().delete()
        rows = []
        for r in ro_df.itertuples(index=False):
            rows.append(RoIndex(
                ro_id=str(r.ro_id),
                budget_code=str(r.budget_code),
                budget_year=int(r.budget_year),
                created_at=_aware(r.created_at.to_pydatetime() if hasattr(r.created_at, "to_pydatetime") else r.created_at),
                amount=_to_decimal(getattr(r, "amount", 0)),
            ))
        RoIndex.objects.bulk_create(rows, batch_size=2000)

    if out_df.empty:
        return 0

    with transaction.atomic():
        # ล้าง BudgetActual ที่มาจาก API ทั้งหมด แล้วเขียนใหม่
        BudgetActual.objects.filter(source="api").delete()
        rows, batch_id, seq = [], f"api_{datetime.now():%Y%m%d%H%M%S}", 0
        for d in out_df.sort_values(["event_ts","doc_date"]).itertuples(index=False):
            seq += 1
            raw_evt = getattr(d, "event_ts", None)
            if hasattr(raw_evt, "to_pydatetime"):
                raw_evt = raw_evt.to_pydatetime()
            event_ts = _aware(raw_evt) if raw_evt is not None else _aware(datetime.combine(d.doc_date.date(), dtime(12,0)))
            rows.append(BudgetActual(
                doc_date      = d.doc_date.date(),
                budget_code   = d.budget_code,
                amount        = _to_decimal(d.amount),
                source        = "api",
                load_batch_id = batch_id,
                event_ts      = event_ts,
                source_ref    = str(getattr(d, "source_ref", "") or ""),
                seq_no        = seq,
            ))
        BudgetActual.objects.bulk_create(rows, batch_size=2000)
    return len(rows)



# ----------------------------------------------------------------
# Remaining Snapshot (สำหรับ Superset)  (คงเดิม)
# ----------------------------------------------------------------
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

    actual_map = {a["budget_code"]: (a["actual_to_date"] or Decimal("0")) for a in actuals}

    with transaction.atomic():
        RemainingSnapshot.objects.filter(budget_year=year).delete()

        rows = []
        for p in plans:
            budget_amt = p["budget_amount"] or Decimal("0")
            used = actual_map.get(p["budget_code"], Decimal("0"))
            usage_pct = None
            if budget_amt and budget_amt != 0:
                try:
                    usage_pct = (Decimal(used) / Decimal(budget_amt))
                    if usage_pct.copy_abs() > Decimal("99999.9999"):
                        usage_pct = Decimal("99999.9999") if usage_pct > 0 else Decimal("-99999.9999")
                    usage_pct = usage_pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                except (InvalidOperation, ZeroDivisionError):
                    usage_pct = None

            remaining = (Decimal(budget_amt) - Decimal(used)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            rows.append(RemainingSnapshot(
                budget_year=year,
                budget_code=p["budget_code"],
                description=p["description"] or "",
                budget_amount=Decimal(budget_amt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                actual_to_date=Decimal(used).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                remaining=remaining,
                usage_pct=usage_pct,
                budget_owner=p.get("budget_owner") or "",
                budget_group=p.get("budget_group") or "",
            ))
        RemainingSnapshot.objects.bulk_create(rows, batch_size=2000)
    return len(rows)






