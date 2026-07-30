from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests


ISTANBUL = ZoneInfo("Europe/Istanbul")
SLACK_SECTION_LIMIT = 2900


def _money(value: float) -> str:
    return f"₺{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _note_blocks(title: str, lines: list[str]) -> list[dict[str, Any]]:
    if not lines:
        return []

    blocks: list[dict[str, Any]] = []
    heading = f"*Not – {title}*"
    current = heading
    for line in lines:
        candidate = f"{current}\n{line}"
        if len(candidate) > SLACK_SECTION_LIMIT and current != heading:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": current}})
            current = f"{heading} _(devam)_\n{line}"
        else:
            current = candidate
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": current}})
    return blocks


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
    detail_blocks: list[dict[str, Any]] = []
    detail_blocks.extend(
        _note_blocks(
            "Fiyatı değişen ürünler",
            [f"• `{item['model']}`: {_money(item['old'])} → {_money(item['new'])}" for item in changed],
        )
    )
    detail_blocks.extend(
        _note_blocks("Yeni ürünler", [f"• `{model}`" for model in summary["new_models"]])
    )
    detail_blocks.extend(
        _note_blocks(
            "Stoktan çıkan ürünler",
            [f"• `{model}`" for model in summary["removed_models"]],
        )
    )
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
            *detail_blocks,
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
