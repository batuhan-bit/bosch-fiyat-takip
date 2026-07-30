from types import SimpleNamespace

from bosch_tracker import slack


def test_slack_message_lists_changed_new_and_removed_products(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url: str, json: dict, timeout: int) -> SimpleNamespace:
        captured.update({"url": url, "payload": json, "timeout": timeout})
        return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/example")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-id")
    monkeypatch.setattr(slack.requests, "post", fake_post)

    slack.send_daily_summary(
        {
            "checked": 10,
            "changed": [
                {"model": "WGG244Z0TR", "old": 34_999, "new": 32_499},
                {"model": "SMS4IKW62T", "old": 29_500.5, "new": 30_000},
            ],
            "new_models": ["NEW123TR"],
            "removed_models": ["OLD456TR"],
            "bosch_unmatched": [],
        }
    )

    texts = [block["text"]["text"] for block in captured["payload"]["blocks"] if block["type"] == "section"]
    assert any("*Fiyatı değişen:* 2" in text for text in texts)
    assert any("`WGG244Z0TR`: ₺34.999,00 → ₺32.499,00" in text for text in texts)
    assert any("`SMS4IKW62T`: ₺29.500,50 → ₺30.000,00" in text for text in texts)
    assert any("*Not – Yeni ürünler*\n• `NEW123TR`" in text for text in texts)
    assert any("*Not – Stoktan çıkan ürünler*\n• `OLD456TR`" in text for text in texts)
    assert captured["url"] == "https://hooks.slack.test/example"
    assert captured["timeout"] == 30


def test_slack_message_omits_empty_note_sections(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url: str, json: dict, timeout: int) -> SimpleNamespace:
        captured["payload"] = json
        return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/example")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-id")
    monkeypatch.setattr(slack.requests, "post", fake_post)

    slack.send_daily_summary(
        {
            "checked": 10,
            "changed": [],
            "new_models": [],
            "removed_models": [],
            "bosch_unmatched": [],
        }
    )

    texts = [block.get("text", {}).get("text", "") for block in captured["payload"]["blocks"]]
    assert not any("*Not –" in text for text in texts)
