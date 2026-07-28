from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .bosch import enrich_from_bosch
from .google_sheets import GoogleSheetsClient
from .http_client import PoliteHttpClient
from .mediamarkt import MediaMarktSource
from .reference_data import load_support, load_wholesale
from .slack import send_daily_summary


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _latest_xlsx(folder: Path) -> Path:
    files = sorted(folder.glob("*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"{folder} içinde Excel dosyası bulunamadı.")
    return files[0]


def run(dry_run: bool, output_json: Path | None) -> None:
    client = PoliteHttpClient()
    products = MediaMarktSource(client).fetch_all()
    for product in products:
        enrich_from_bosch(product, client)

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps([p.as_dict() for p in products], ensure_ascii=False, indent=2), encoding="utf-8")

    if dry_run:
        wholesale_file = Path(os.getenv("WHOLESALE_FILE", "")) if os.getenv("WHOLESALE_FILE") else _latest_xlsx(PROJECT_ROOT / "girdiler/toptan-fiyat-listeleri")
        support_file = Path(os.getenv("SUPPORT_FILE", "")) if os.getenv("SUPPORT_FILE") else _latest_xlsx(PROJECT_ROOT / "girdiler/fiyat-farki-listeleri")
        wholesale = load_wholesale(wholesale_file)
        support = load_support(support_file)
        print(json.dumps({"products": len(products), "wholesale": len(wholesale), "support": len(support)}, ensure_ascii=False))
        return

    sheets = GoogleSheetsClient()
    try:
        wholesale, support = sheets.read_reference_data()
        summary = sheets.write_current_and_history(products, wholesale, support)
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

