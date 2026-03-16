import os
import re
import logging
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from analytics.tasks import etl_budget_all
from analytics.models import RemainingSnapshot, BudgetPlan, BudgetActual, RoIndex
from .embed_token import mint_guest_token

# LINE Bot SDK v3
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest
from linebot.v3.messaging.models import (
    TextMessage,
    FlexMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.exceptions import InvalidSignatureError

logger = logging.getLogger(__name__)


# ----------------------------------------
# Helper: สรุป RO (รวมมุมรหัสงบ + budget_owner)
# ----------------------------------------
def summarize_ro(ro_id: str):
    try:
        ro = RoIndex.objects.get(pk=str(ro_id))
    except RoIndex.DoesNotExist:
        return {"found": False, "message": f"ไม่พบ RO: {ro_id}"}

    code = ro.budget_code
    year = ro.budget_year
    ro_amount = ro.amount or Decimal("0")
    ro_ts = ro.created_at

    plan = BudgetPlan.objects.filter(budget_year=year, budget_code=code).first()
    plan_amount = plan.budget_amount if plan else Decimal("0")
    owner = (plan.budget_owner if plan else "") or ""

    used_code = (
        BudgetActual.objects
        .filter(budget_code=code, event_ts__lte=ro_ts)
        .aggregate(s=Sum("amount"))["s"] or Decimal("0")
    )
    remaining_code = plan_amount - used_code

    plan_owner_total = used_owner_total = remaining_owner_total = Decimal("0")
    if owner:
        owner_codes = list(
            BudgetPlan.objects.filter(budget_year=year, budget_owner=owner)
            .values_list("budget_code", flat=True)
        )
        plan_owner_total = (
            BudgetPlan.objects
            .filter(budget_year=year, budget_owner=owner)
            .aggregate(s=Sum("budget_amount"))["s"] or Decimal("0")
        )
        used_owner_total = (
            BudgetActual.objects
            .filter(budget_code__in=owner_codes, event_ts__lte=ro_ts)
            .aggregate(s=Sum("amount"))["s"] or Decimal("0")
        )
        remaining_owner_total = plan_owner_total - used_owner_total

    return {
        "found": True,
        "ro_id": ro.ro_id,
        "budget_year": year,
        "budget_code": code,
        "budget_owner": owner or None,
        "ro_amount": ro_amount,
        "plan_amount_code": plan_amount,
        "used_incl_ro_code": used_code,
        "remaining_code": remaining_code,
        "plan_amount_owner": plan_owner_total,
        "used_incl_ro_owner": used_owner_total,
        "remaining_owner": remaining_owner_total,
    }


# ----------------------------------------
# Flex builder + สัญญาณเตือน <10%
# ----------------------------------------
def _pct(remaining: Decimal, base: Decimal) -> Decimal:
    if not base or base == 0:
        return Decimal("0")
    return (Decimal(remaining) / Decimal(base)).quantize(Decimal("0.0001"))

def _warn_block(label: str):
    # กล่องเตือนพื้นหลังสีชมพูอ่อน
    return {
        "type": "box",
        "layout": "horizontal",
        "backgroundColor": "#FDECEC",
        "cornerRadius": "md",
        "paddingAll": "8px",
        "contents": [
            {"type": "text", "text": "⚠", "size": "md", "weight": "bold", "flex": 0, "margin": "sm"},
            {"type": "text", "text": f"คงเหลือ < 10% ({label})", "weight": "bold", "color": "#C81E1E", "wrap": True}
        ]
    }

def build_ro_flex(result: dict) -> dict:
    # คำนวณเปอร์เซ็นต์คงเหลือ (รหัสงบ)
    code_base = result["plan_amount_code"]
    code_rem = result["remaining_code"]
    code_rem_pct = _pct(code_rem, code_base)

    # ถ้ามี owner ให้คำนวณด้วย
    owner_warn = None
    owner_rows = []
    if result.get("budget_owner"):
        owner_base = result["plan_amount_owner"]
        owner_rem = result["remaining_owner"]
        owner_rem_pct = _pct(owner_rem, owner_base)
        if owner_base and owner_rem_pct < Decimal("0.10"):
            owner_warn = _warn_block(f"ตาม budget_owner: {result['budget_owner']}")
        owner_rows = [
            {"type":"separator","margin":"md"},
            {"type":"text","text":f"ตาม budget_owner: {result['budget_owner']}", "weight":"bold", "size":"sm", "margin":"sm"},
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"งบทั้งปี","flex":2},
                {"type":"text","text":f"{Decimal(owner_base):,.2f}","flex":3,"align":"end"}
            ]},
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"ใช้ไปแล้ว (รวม RO)","flex":2},
                {"type":"text","text":f"{Decimal(result['used_incl_ro_owner']):,.2f}","flex":3,"align":"end"}
            ]},
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"คงเหลือ","flex":2},
                {"type":"text","text":f"{Decimal(owner_rem):,.2f}","flex":3,"align":"end"}
            ]},
        ]
        if owner_warn:
            owner_rows.insert(0, {"type":"spacer","size":"sm"})
            owner_rows.insert(1, owner_warn)

    # กล่องเตือนสำหรับรหัสงบ
    code_warn = _warn_block("ตามรหัสงบ") if (code_base and code_rem_pct < Decimal("0.10")) else None

    body_contents = [
        {"type":"text","text":f"RO #{result['ro_id']}", "weight":"bold","size":"lg"},
        {"type":"separator","margin":"md"},
        {"type":"box","layout":"vertical","margin":"md","contents":[
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"ยอดสั่งซื้อ (RO)","flex":2},
                {"type":"text","text":f"{Decimal(result['ro_amount']):,.2f}","flex":3,"align":"end"}
            ]},
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"ปีงบประมาณ","flex":2},
                {"type":"text","text":str(result['budget_year']),"flex":3,"align":"end"}
            ]},
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"รหัสงบ","flex":2},
                {"type":"text","text":result['budget_code'],"flex":3,"align":"end"}
            ]},
            {"type":"separator","margin":"md"},
            {"type":"text","text":"ตามรหัสงบ","weight":"bold","size":"sm","margin":"sm"},
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"งบทั้งปี","flex":2},
                {"type":"text","text":f"{Decimal(code_base):,.2f}","flex":3,"align":"end"}
            ]},
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"ใช้ไปแล้ว (รวม RO)","flex":2},
                {"type":"text","text":f"{Decimal(result['used_incl_ro_code']):,.2f}","flex":3,"align":"end"}
            ]},
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":"คงเหลือ","flex":2},
                {"type":"text","text":f"{Decimal(code_rem):,.2f}","flex":3,"align":"end"}
            ]},
        ]}
    ]

    if code_warn:
        body_contents.insert(3, {"type":"spacer","size":"sm"})
        body_contents.insert(4, code_warn)

    if owner_rows:
        body_contents.append({"type":"box","layout":"vertical","margin":"sm","contents": owner_rows})

    bubble = {"type":"bubble","body":{"type":"box","layout":"vertical","contents": body_contents}}
    return bubble


# ----------------------------------------
# Control Panel + Superset embed
# ----------------------------------------
@require_http_methods(["GET", "POST"])
def control_panel(request):
    if request.method == "POST":
        try:
            r = etl_budget_all.delay()
            messages.success(request, "สั่งรัน ETL แล้ว! โปรดรีเฟรช Dashboard ในอีกสักครู่")
            logger.info("Manual ETL queued: task_id=%s user=%s", getattr(r, "id", None), getattr(request.user, "username", "anon"))
        except Exception as e:
            logger.exception("Queue ETL failed: %s", e)
            messages.error(request, f"สั่งรัน ETL ไม่สำเร็จ: {e}")
        return redirect("analytics:control_panel")

    latest = (
        RemainingSnapshot.objects
        .order_by("-snapshot_at")
        .values("snapshot_at", "budget_year")
        .first()
    )
    return render(request, "analytics/control_panel.html", {
        "superset_url": os.getenv("SUPERSET_BASE_URL", getattr(settings, "SUPERSET_BASE_URL", "")),
        "latest": latest,
    })


def embed_dashboard(request):
    ctx = {
        "superset_url": os.getenv("SUPERSET_BASE_URL", getattr(settings, "SUPERSET_BASE_URL", "")),
        "dash_id": os.getenv("SUPERSET_EMBED_DASHBOARD_ID", getattr(settings, "SUPERSET_EMBED_DASHBOARD_ID", "")) or "",
    }
    resp = render(request, "analytics/embed_dashboard.html", ctx)

    # ตั้ง Referrer-Policy จาก settings / .env (ไม่ hard-code)
    policy = getattr(settings, "EMBED_REFERRER_POLICY", None) \
             or getattr(settings, "SECURE_REFERRER_POLICY", None) \
             or "strict-origin-when-cross-origin"
    resp["Referrer-Policy"] = policy
    return resp


@require_GET
def superset_guest_token(request):
    dash_id = os.getenv("SUPERSET_EMBED_DASHBOARD_ID", getattr(settings, "SUPERSET_EMBED_DASHBOARD_ID", "")) or ""
    if not dash_id:
        return HttpResponseBadRequest("Missing SUPERSET_EMBED_DASHBOARD_ID")
    username = getattr(request.user, "username", "") or "guest"
    token = mint_guest_token(dash_id, username=username)
    return JsonResponse({"token": token})


# ----------------------------------------
# LINE OA: คำสั่งง่าย ๆ + โหมดทดสอบผ่านเว็บ
# ----------------------------------------
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

def _fmt(n):
    try:
        return f"{Decimal(n):,.2f}"
    except Exception:
        return str(n)

def _help_text():
    return (
        "เมนูใช้งาน:\n"
        "- พิมพ์เลข RO เช่น 123456 เพื่อดูสถานะงบของ RO นั้น\n"
        "- owner <ชื่อเจ้าของงบ> เช่น owner กองช่าง เพื่อดูภาพรวมตามเจ้าของงบ\n"
        "- help เพื่อดูเมนูนี้อีกครั้ง"
    )

def _parse_text_command(text: str):
    """
    คืน (kind, payload)
    kind: 'help' | 'owner' | 'ro' | 'unknown'
    """
    t = (text or "").strip()
    if not t:
        return ("help", None)

    if re.match(r"^(help|เมนู)$", t, flags=re.I):
        return ("help", None)

    m_owner = re.match(r"^(owner|เจ้าของงบ)\s+(.+)$", t, flags=re.I)
    if m_owner:
        return ("owner", m_owner.group(2).strip())

    # ถ้าเป็นตัวเลขล้วน >= 3 หลัก ให้ตีความเป็น RO
    if re.match(r"^\d{3,}$", t):
        return ("ro", t)

    return ("unknown", t)


def summarize_owner(owner: str, year: int | None = None):
    """
    สรุปรวมตาม budget_owner (ง่าย ๆ ณ ปัจจุบัน)
    ถ้าไม่ระบุปี จะหา 'ปีล่าสุด' ที่มีใน BudgetPlan ของ owner นั้น
    """
    qs_plan = BudgetPlan.objects.filter(budget_owner=owner)
    if year:
        qs_plan = qs_plan.filter(budget_year=year)

    latest_year = qs_plan.order_by("-budget_year").values_list("budget_year", flat=True).first()
    if not latest_year:
        return {"found": False, "message": f"ไม่พบแผนงบของ owner: {owner}"}

    owner_codes = list(
        BudgetPlan.objects
        .filter(budget_owner=owner, budget_year=latest_year)
        .values_list("budget_code", flat=True)
    )

    plan_total = (
        BudgetPlan.objects
        .filter(budget_owner=owner, budget_year=latest_year)
        .aggregate(s=Sum("budget_amount"))["s"] or Decimal("0")
    )
    used_total = (
        BudgetActual.objects
        .filter(budget_code__in=owner_codes)
        .aggregate(s=Sum("amount"))["s"] or Decimal("0")
    )
    remaining = plan_total - used_total

    # Top 5 codes ตามวงเงินแผน
    top_rows = (
        BudgetPlan.objects
        .filter(budget_owner=owner, budget_year=latest_year)
        .values("budget_code")
        .annotate(plan=Sum("budget_amount"))
        .order_by("-plan")[:5]
    )

    top_detail = []
    for row in top_rows:
        code = row["budget_code"]
        plan = row["plan"] or Decimal("0")
        used = (
            BudgetActual.objects
            .filter(budget_code=code)
            .aggregate(s=Sum("amount"))["s"] or Decimal("0")
        )
        top_detail.append({
            "code": code,
            "plan": plan,
            "used": used,
            "remaining": plan - used,
        })

    return {
        "found": True,
        "budget_owner": owner,
        "budget_year": latest_year,
        "plan_total": plan_total,
        "used_total": used_total,
        "remaining": remaining,
        "top_detail": top_detail,
    }

def build_owner_flex(result: dict) -> dict:
    """
    Flex สำหรับ owner รวม + top 5 codes
    """
    header = [
        {"type":"text","text":f"Owner: {result['budget_owner']}", "weight":"bold","size":"lg"},
        {"type":"text","text":f"ปีงบประมาณ: {result['budget_year']}", "size":"sm", "color":"#666666"},
        {"type":"separator","margin":"md"},
    ]
    summary = [
        {"type":"box","layout":"baseline","contents":[
            {"type":"text","text":"งบทั้งปี","flex":2},
            {"type":"text","text":_fmt(result["plan_total"]), "flex":3,"align":"end"}
        ]},
        {"type":"box","layout":"baseline","contents":[
            {"type":"text","text":"ใช้ไปแล้ว","flex":2},
            {"type":"text","text":_fmt(result["used_total"]), "flex":3,"align":"end"}
        ]},
        {"type":"box","layout":"baseline","contents":[
            {"type":"text","text":"คงเหลือ","flex":2},
            {"type":"text","text":_fmt(result["remaining"]), "flex":3,"align":"end"}
        ]},
        {"type":"separator","margin":"md"},
        {"type":"text","text":"Top 5 codes","weight":"bold","size":"sm","margin":"sm"},
    ]

    rows = []
    for i, r in enumerate(result.get("top_detail") or [], start=1):
        rows += [
            {"type":"box","layout":"baseline","contents":[
                {"type":"text","text":f"{i}) {r['code']}", "flex":2},
                {"type":"text","text":_fmt(r["remaining"]), "flex":3, "align":"end"}
            ]},
        ]

    body = {"type":"box","layout":"vertical","contents": header + summary + rows}
    return {"type":"bubble","body": body}


@csrf_exempt
@require_http_methods(["POST"])
def line_webhook(request):
    """
    รองรับ:
    - "<เลข RO>" → รายละเอียด RO + สถานะงบ (summarize_ro + build_ro_flex)
    - "owner <ชื่อ>" → ภาพรวมตามเจ้าของงบ + top 5 codes
    - "help"/"เมนู" หรือไม่เข้าใจ → แสดงวิธีใช้
    """
    if not CHANNEL_SECRET or not CHANNEL_ACCESS_TOKEN:
        return HttpResponseBadRequest("LINE credentials are not configured")

    signature = request.headers.get("X-Line-Signature", "")
    body = request.body.decode("utf-8")

    parser = WebhookParser(CHANNEL_SECRET)
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        return HttpResponseForbidden("Invalid signature")
    except Exception as e:
        logger.exception("Parse error: %s", e)
        return HttpResponseBadRequest("Cannot parse request body")

    config = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
    with ApiClient(config) as api_client:
        line_api = MessagingApi(api_client)

        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                text = (event.message.text or "").strip()
                kind, payload = _parse_text_command(text)

                quick = QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="help", text="help")),
                    QuickReplyItem(action=MessageAction(label="owner ตัวอย่าง", text="owner กองช่าง")),
                ])

                if kind == "help":
                    line_api.reply_message(ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=_help_text(), quickReply=quick)]
                    ))
                    continue

                if kind == "owner":
                    result = summarize_owner(payload)
                    if not result.get("found"):
                        line_api.reply_message(ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=result.get("message", "ไม่พบข้อมูล"), quickReply=quick)]
                        ))
                        continue
                    try:
                        bubble = build_owner_flex(result)
                        flex = FlexMessage(alt_text=f"ภาพรวม owner: {result['budget_owner']}", contents=bubble)
                        line_api.reply_message(ReplyMessageRequest(
                            reply_token=event.reply_token, messages=[flex]
                        ))
                    except Exception as e:
                        logger.warning("Owner flex failed, fallback: %s", e)
                        msg = (
                            f"[Owner: {result['budget_owner']}] ปี {result['budget_year']}\n"
                            f"- งบทั้งปี: {_fmt(result['plan_total'])}\n"
                            f"- ใช้ไปแล้ว: {_fmt(result['used_total'])}\n"
                            f"- คงเหลือ: {_fmt(result['remaining'])}\n"
                        )
                        line_api.reply_message(ReplyMessageRequest(
                            reply_token=event.reply_token, messages=[TextMessage(text=msg)]
                        ))
                    continue

                if kind == "ro":
                    ro_id = payload
                    result = summarize_ro(ro_id)
                    if not result.get("found"):
                        line_api.reply_message(ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=result.get("message", "ไม่พบข้อมูล"), quickReply=quick)]
                        ))
                        continue
                    try:
                        bubble = build_ro_flex(result)
                        flex = FlexMessage(alt_text="รายละเอียด RO และสถานะงบ", contents=bubble)
                        line_api.reply_message(ReplyMessageRequest(
                            reply_token=event.reply_token, messages=[flex]
                        ))
                    except Exception as e:
                        logger.warning("RO flex failed, fallback: %s", e)
                        lines = [
                            f"RO #{result['ro_id']}",
                            f"ปีงบประมาณ: {result['budget_year']}",
                            f"รหัสงบ: {result['budget_code']}",
                            f"ยอดสั่งซื้อ (RO): {_fmt(result['ro_amount'])}",
                            "------------------------------",
                            "[ตามรหัสงบ]",
                            f"- งบทั้งปี: {_fmt(result['plan_amount_code'])}",
                            f"- ใช้ไปแล้ว (รวม RO): {_fmt(result['used_incl_ro_code'])}",
                            f"- คงเหลือ: {_fmt(result['remaining_code'])}",
                        ]
                        if result.get("budget_owner"):
                            lines += [
                                "------------------------------",
                                f"[ตาม budget_owner: {result['budget_owner']}]",
                                f"- งบทั้งปี: {_fmt(result['plan_amount_owner'])}",
                                f"- ใช้ไปแล้ว (รวม RO): {_fmt(result['used_incl_ro_owner'])}",
                                f"- คงเหลือ: {_fmt(result['remaining_owner'])}",
                            ]
                        line_api.reply_message(ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text="\n".join(lines))]
                        ))
                    continue

                # unknown → แสดงเมนู
                line_api.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=_help_text(), quickReply=quick)]
                ))

    return HttpResponse("OK")


@require_GET
def line_debug(request):
    """
    โหมดทดสอบผ่านเว็บ (ไม่ต้องใช้ลายเซ็นจาก LINE):
      /analytics/line/debug?text=owner กองช่าง
      /analytics/line/debug?text=123456
      /analytics/line/debug?text=help
    """
    text = (request.GET.get("text") or "").strip()
    if not text:
        return JsonResponse({"hint": "ใส่ ?text=... เช่น ?text=owner กองช่าง หรือ ?text=123456"})

    kind, payload = _parse_text_command(text)
    if kind == "help":
        return JsonResponse({"kind": kind, "text": _help_text()})

    if kind == "owner":
        return JsonResponse({"kind": kind, "result": summarize_owner(payload)})

    if kind == "ro":
        return JsonResponse({"kind": kind, "result": summarize_ro(payload)})

    return JsonResponse({"kind": "unknown", "text": text})


# ----------------------------------------
# DEV: ดูไฟล์ export ล่าสุดจาก API (raw + normalize)
# เปิดเฉพาะเมื่อ ANALYTICS_DEBUG_VIEW=1 หรือ settings.DEBUG=True
# ----------------------------------------
@require_GET
# @login_required
def debug_api_latest(request):
    # อนุญาตเฉพาะตอน dev เท่านั้น
    if not (getattr(settings, "DEBUG", False) or os.getenv("ANALYTICS_DEBUG_VIEW") == "1"):
        return HttpResponseForbidden("Debug view disabled")

    base = getattr(settings, "DATA_ROOT", None)
    if not base:
        base = Path(getattr(settings, "BASE_DIR")) / "data"
    outdir = Path(base) / "dev_exports"
    latest_flag = outdir / "latest.txt"

    if not latest_flag.exists():
        return JsonResponse({
            "status": "no_export_found",
            "expected_dir": str(outdir),
            "hint": "Run ETL after setting ANALYTICS_DEBUG_EXPORT_API=1 and API_PSL_RECORDS_URL"
        }, status=404)

    ts = latest_flag.read_text(encoding="utf-8").strip()
    raw_path = outdir / f"api_raw_{ts}.json"
    norm_path = outdir / f"api_norm_{ts}.csv"

    resp = {
        "timestamp": ts,
        "raw_path": str(raw_path) if raw_path.exists() else None,
        "norm_path": str(norm_path) if norm_path.exists() else None,
    }

    if raw_path.exists():
        resp["raw_preview"] = raw_path.read_text(encoding="utf-8")[:2048]

    if norm_path.exists():
        try:
            import pandas as pd
            head = pd.read_csv(norm_path, nrows=5)
            resp["norm_head"] = head.to_dict(orient="records")
        except Exception as e:
            resp["norm_error"] = str(e)

    return JsonResponse(resp)








