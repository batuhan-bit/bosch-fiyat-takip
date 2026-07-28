from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from .models import ProductPrice, ReferenceValue
from .parsing import as_float, normalize_model


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CURRENT_SHEET = "Güncel Fiyatlar"
HISTORY_SHEET = "Fiyat Geçmişi"
WHOLESALE_SHEET = "Toptan Fiyat Listesi"
SUPPORT_SHEET = "Bosch Destekleri"
ERROR_SHEET = "Ayarlar ve Hatalar"
ISTANBUL = ZoneInfo("Europe/Istanbul")

CURRENT_HEADERS = [
    "Ürün Modeli",
    "Kategori",
    "MediaMarkt Fiyatı",
    "Bosch Satış Fiyatı",
    "Toptan Fiyatımız",
    "Son Alış Fiyatımız",
    "Son Alış Tarihi",
    "Bosch Fiyat Farkı Desteği (KDV Hariç)",
    "Net Toptan Fiyat",
    "Net Son Alış Fiyatı",
    "Toptan Liste Durumu",
    "Destek Kaynağı",
    "Son Kontrol Tarihi",
    "MediaMarkt Linki",
    "Bosch Linki",
]


def _credentials_from_env() -> Credentials:
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"].strip()
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        info = json.loads(base64.b64decode(raw).decode("utf-8"))
    return Credentials.from_service_account_info(info, scopes=SCOPES)


class GoogleSheetsClient:
    def __init__(self) -> None:
        self.spreadsheet_id = os.environ["GOOGLE_SHEET_ID"].strip()
        self.service = build("sheets", "v4", credentials=_credentials_from_env(), cache_discovery=False)
        self.values = self.service.spreadsheets().values()

    def _get(self, range_name: str) -> list[list[Any]]:
        response = self.values.get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueRenderOption="UNFORMATTED_VALUE",
        ).execute()
        return response.get("values", [])

    def read_reference_data(self) -> tuple[dict[str, ReferenceValue], dict[str, ReferenceValue]]:
        wholesale: dict[str, ReferenceValue] = {}
        for row in self._get(f"'{WHOLESALE_SHEET}'!A2:D"):
            if len(row) >= 2 and isinstance(row[1], (int, float)):
                model = normalize_model(str(row[0]))
                wholesale[model] = ReferenceValue(
                    model, float(row[1]), "Toptan", str(row[2]) if len(row) > 2 else "", str(row[3]) if len(row) > 3 else ""
                )

        support: dict[str, ReferenceValue] = {}
        for row in self._get(f"'{SUPPORT_SHEET}'!A2:E"):
            if len(row) >= 3 and isinstance(row[1], (int, float)):
                model = normalize_model(str(row[0]))
                support[model] = ReferenceValue(
                    model, float(row[1]), str(row[2]), str(row[3]) if len(row) > 3 else "", str(row[4]) if len(row) > 4 else ""
                )
        return wholesale, support

    def _current_rows(self) -> list[list[Any]]:
        return self._get(f"'{CURRENT_SHEET}'!A2:O")

    def _latest_manual_values(self) -> dict[str, tuple[Any, Any]]:
        latest: dict[str, tuple[Any, Any]] = {}
        for row in self._get(f"'{HISTORY_SHEET}'!B2:H"):
            if not row:
                continue
            model = normalize_model(str(row[0]))
            manual_last = row[5] if len(row) > 5 else ""
            manual_last_date = row[6] if len(row) > 6 else ""
            latest[model] = (manual_last, manual_last_date)
        return latest

    def write_current_and_history(
        self,
        products: list[ProductPrice],
        wholesale: dict[str, ReferenceValue],
        support: dict[str, ReferenceValue],
    ) -> dict[str, Any]:
        old_rows = self._current_rows()
        old_by_model = {normalize_model(str(row[0])): row for row in old_rows if row}
        historical_manual = self._latest_manual_values()
        now = datetime.now(ISTANBUL).strftime("%Y-%m-%d %H:%M:%S")
        rows: list[list[Any]] = []
        history_rows: list[list[Any]] = []
        changed: list[dict[str, Any]] = []
        new_models: list[str] = []
        seen: set[str] = set()

        for product in products:
            model = product.model
            seen.add(model)
            old = old_by_model.get(model, [])
            historical_last, historical_last_date = historical_manual.get(model, ("", ""))
            manual_last = old[5] if old and len(old) > 5 else historical_last
            manual_last_date = old[6] if old and len(old) > 6 else historical_last_date
            wholesale_value = wholesale.get(model)
            support_value = support.get(model)
            wholesale_cell: Any = wholesale_value.amount if wholesale_value else "YOK"
            support_cell: Any = support_value.amount if support_value else "YOK"
            bosch_price: Any = product.bosch_price if product.bosch_price is not None else "YOK"
            mediamarkt_price: Any = product.mediamarkt_price if product.mediamarkt_price is not None else "YOK"
            support_amount = support_value.amount if support_value else 0.0
            net_wholesale_value: Any = wholesale_value.amount - support_amount if wholesale_value else "YOK"
            manual_last_number = as_float(manual_last)
            net_last_value: Any = manual_last_number - support_amount if manual_last_number is not None else ""
            wholesale_status = "Listede" if wholesale_value else "Toptan listede yok"
            support_source = support_value.source_type if support_value else "YOK"
            row_number = len(rows) + 2
            net_wholesale = f'=IF(E{row_number}="YOK";"YOK";E{row_number}-IF(ISNUMBER(H{row_number});H{row_number};0))'
            net_last = f'=IF(F{row_number}="";"";F{row_number}-IF(ISNUMBER(H{row_number});H{row_number};0))'
            row = [
                model,
                product.category,
                mediamarkt_price,
                bosch_price,
                wholesale_cell,
                manual_last,
                manual_last_date,
                support_cell,
                net_wholesale,
                net_last,
                wholesale_status,
                support_source,
                now,
                product.mediamarkt_url,
                product.bosch_url,
            ]
            rows.append(row)
            history_rows.append(
                [
                    now,
                    model,
                    product.category,
                    mediamarkt_price,
                    bosch_price,
                    wholesale_cell,
                    manual_last,
                    manual_last_date,
                    support_cell,
                    net_wholesale_value,
                    net_last_value,
                    wholesale_status,
                    support_source,
                    product.mediamarkt_url,
                    product.bosch_url,
                ]
            )

            if not old:
                new_models.append(model)
            else:
                old_price = as_float(old[2] if len(old) > 2 else None)
                if old_price is not None and product.mediamarkt_price is not None and old_price != product.mediamarkt_price:
                    changed.append({"model": model, "old": old_price, "new": product.mediamarkt_price})

        removed_models = sorted(set(old_by_model) - seen)

        self.values.clear(spreadsheetId=self.spreadsheet_id, range=f"'{CURRENT_SHEET}'!A2:O").execute()
        if rows:
            self.values.update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{CURRENT_SHEET}'!A2:O{len(rows)+1}",
                valueInputOption="USER_ENTERED",
                body={"values": rows},
            ).execute()
        if history_rows:
            self.values.append(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{HISTORY_SHEET}'!A:O",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": history_rows},
            ).execute()
        return {
            "checked": len(products),
            "changed": changed,
            "new_models": new_models,
            "removed_models": removed_models,
            "bosch_unmatched": [p.model for p in products if "bulunamadı" in p.bosch_status],
        }

    def update_reference_data(
        self,
        wholesale: dict[str, ReferenceValue],
        support: dict[str, ReferenceValue],
    ) -> None:
        wholesale_rows = [[v.model, v.amount, v.period, v.source_file] for v in sorted(wholesale.values(), key=lambda item: item.model)]
        support_rows = [[v.model, v.amount, v.source_type, v.period, v.source_file] for v in sorted(support.values(), key=lambda item: item.model)]
        for sheet, columns, rows in (
            (WHOLESALE_SHEET, "A2:D", wholesale_rows),
            (SUPPORT_SHEET, "A2:E", support_rows),
        ):
            self.values.clear(spreadsheetId=self.spreadsheet_id, range=f"'{sheet}'!{columns}").execute()
            if rows:
                self.values.update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{sheet}'!A2",
                    valueInputOption="USER_ENTERED",
                    body={"values": rows},
                ).execute()

    def log_error(self, stage: str, message: str, model: str = "", url: str = "") -> None:
        self.values.append(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{ERROR_SHEET}'!A:E",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [[datetime.now(ISTANBUL).isoformat(timespec="seconds"), stage, model, message[:1000], url]]},
        ).execute()
