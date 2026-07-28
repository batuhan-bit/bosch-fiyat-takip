from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from bs4 import BeautifulSoup


MODEL_RE = re.compile(r"\b[KSWT][A-Z0-9]{7,14}\b", re.IGNORECASE)


def normalize_model(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def looks_like_model(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = normalize_model(value)
    return (
        8 <= len(normalized) <= 15
        and normalized[0] in "KSWT"
        and any(char.isdigit() for char in normalized)
        and any(char.isalpha() for char in normalized)
    )


def extract_model(text: str) -> str | None:
    match = MODEL_RE.search(text.upper())
    return normalize_model(match.group(0)) if match else None


def json_ld_objects(html: str) -> Iterable[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            yield value
        elif isinstance(value, list):
            yield from (item for item in value if isinstance(item, dict))


def schema_type(value: dict[str, Any]) -> set[str]:
    raw = value.get("@type")
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {item for item in raw if isinstance(item, str)}
    return set()


def first_offer(offers: object) -> dict[str, Any]:
    if isinstance(offers, dict):
        return offers
    if isinstance(offers, list):
        return next((offer for offer in offers if isinstance(offer, dict)), {})
    return {}


def as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("₺", "").replace(" ", "")
        if not cleaned:
            return None
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

