from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .bosch import enrich_from_bosch
from .google_sheets import GoogleSheetsClient
from .http_client import PoliteHttpClient
from .mediamarkt import MediaMarktSource
from .store_stock import enrich_store_stock
from .slack import send_daily_summary

def run(dry_run: bool, output_json: Path | None) -> None:
    client = PoliteHttpClient()
    products = MediaMarktSource(client).fetch_all()
    for product in products:
        enrich_store_stock(product, client)
        enrich_from_bosch(product, client)

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps([p.as_dict() for p in products], ensure_ascii=False, indent=2), encoding="utf-8")

    if dry_run:
        print(json.dumps({"products": len(products)}, ensure_ascii=False))
        return

    sheets = GoogleSheetsClient()
    try:
        wholesale, support, stock = sheets.read_reference_data()
        summary = sheets.write_current_and_history(products, wholesale, support, stock)
        if os.getenv("SKIP_SLACK", "").casefold() not in {"1", "true", "yes"}:
            send_daily_summary(summary)
    except Exception as exc:
        try:
            sheets.log_error("Günlük çalışma", str(exc))
        finally:
            raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Google Sheets ve Slack'e yazmadan çalıştır")
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    run(args.dry_run, args.output_json)


if __name__ == "__main__":
    main()
