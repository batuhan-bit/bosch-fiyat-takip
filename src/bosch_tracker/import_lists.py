from __future__ import annotations

import argparse
from pathlib import Path

from .google_sheets import GoogleSheetsClient
from .reference_data import load_support, load_wholesale


def main() -> None:
    parser = argparse.ArgumentParser(description="Aylık Bosch listelerini Google Sheets'e aktar")
    parser.add_argument("--wholesale", type=Path, required=True)
    parser.add_argument("--support", type=Path, required=True)
    args = parser.parse_args()
    wholesale = load_wholesale(args.wholesale)
    support = load_support(args.support)
    GoogleSheetsClient().update_reference_data(wholesale, support)
    print(f"{len(wholesale)} toptan fiyatı ve {len(support)} destek tutarı aktarıldı.")


if __name__ == "__main__":
    main()

