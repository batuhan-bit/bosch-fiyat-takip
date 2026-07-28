from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests


ISTANBUL = ZoneInfo("Europe/Istanbul")


def _money(value: float) -> str:
    return f"₺{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def send_daily_summary(summary: dict[str, Any]) -> None:
    webhook = os.environ["SLACK_WEBHOOK_URL"].strip()
    sheet_id = os.environ["GOOGLE_SHEET_ID"].strip()
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    changed = summary["changed"]
    lines = [
        f"*MediaMarkt'ta satılabilir ürün:* {summary['checked']}",
        f"*Fiyatı değişen:* {len(changed)}",
        f"*Yeni ürün:* {len(summary['new_models'])}",
        f"*Stoktan çıkan ürün:* {len(summary['removed_models'])}",
        f"*Bosch sitesinde eşleşmeyen:* {len(summary['bosch_unmatched'])}",
    ]
    if changed:
        lines.append("\n*MediaMarkt fiyat değişiklikleri*")
        for item in changed[:15]:
            lines.append(f"• `{item['model']}`: {_money(item['old'])} → {_money(item['new'])}")
        if len(changed) > 15:
            lines.append(f"• … ve {len(changed) - 15} değişiklik daha")
    payload = {
        "text": "Bosch günlük fiyat takip raporu",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Bosch Günlük Fiyat Takibi", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tarih:* {datetime.now(ISTANBUL):%d.%m.%Y %H:%M}\n" + "\n".join(lines),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Google Sheets'i Aç"}, "url": sheet_url}
                ],
            },
        ],
    }
    response = requests.post(webhook, json=payload, timeout=30)
    response.raise_for_status()
