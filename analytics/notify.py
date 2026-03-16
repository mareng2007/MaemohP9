import os
import pandas as pd
from django.conf import settings
from analytics.models import RemainingSnapshot

from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
)

def fetch_top_usage(n=10) -> pd.DataFrame:
    latest = (
        RemainingSnapshot.objects
        .order_by("-snapshot_at")
        .values_list("snapshot_at", flat=True)
        .first()
    )
    if not latest:
        return pd.DataFrame(columns=[
            "budget_code", "description", "budget_amount",
            "actual_to_date", "remaining", "usage_pct"
        ])

    qs = (
        RemainingSnapshot.objects
        .filter(snapshot_at=latest)
        .order_by("-usage_pct")
        .values("budget_code", "description", "budget_amount",
                "actual_to_date", "remaining", "usage_pct")[:n]
    )
    return pd.DataFrame(list(qs))

def format_message(df: pd.DataFrame, title="Budget Usage Alert") -> str:
    if df.empty:
        return f"{title}\n(ยังไม่มีข้อมูล snapshot)"
    lines = [title]
    for _, r in df.iterrows():
        pct = float(r["usage_pct"] or 0) * 100
        lines.append(
            f'{r["budget_code"]} {str(r["description"] or "")[:28]} | '
            f'Used {float(r["actual_to_date"]):,.0f} / {float(r["budget_amount"]):,.0f} '
            f'({pct:.1f}%) | Rem {float(r["remaining"]):,.0f}'
        )
    return "\n".join(lines)

def push_line_message(text: str):
    channel_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    targets = getattr(settings, "LINE_TARGET_IDS", [])

    if not channel_token or not targets:
        raise RuntimeError("ต้องตั้งค่า LINE_CHANNEL_ACCESS_TOKEN และ LINE_TARGET_IDS ใน ENV/Settings")

    config = Configuration(access_token=channel_token)
    with ApiClient(config) as client:
        api = MessagingApi(client)
        for to_id in targets:
            to_id = str(to_id).strip()
            if not to_id:
                continue
            api.push_message(
                PushMessageRequest(
                    to=to_id,
                    messages=[TextMessage(text=text)]
                )
            )

