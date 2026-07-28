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
STOCK_SHEET = "Eldem Stok Raporu"
MANUAL_ARCHIVE_SHEET = "Son Alış Arşivi"
ERROR_SHEET = "Ayarlar ve Hatalar"
ISTANBUL = ZoneInfo("Europe/Istanbul")

CURRENT_HEADERS = [
    "Ürün Modeli",
    "Kategori",
    "MediaMarkt Fiyatı",
    "Espark Stok",
    "Vega Stok",
    "Bosch Satış Fiyatı",
    "Eldem Stok",
    "Toptan Fiyatımız",
    "Son Alış Fiyatımız",
    "Son Alış Tarihi",
    "Bosch Fiyat Farkı Desteği (KDV Hariç)",
    "Net Toptan Fiyat",
    "Net Toptana Göre Karlılık",
    "Net Son Alış Fiyatı",
    "Net Son Alışa Göre Karlılık",
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

    def read_reference_data(
        self,
    ) -> tuple[dict[str, ReferenceValue], dict[str, ReferenceValue], dict[str, float]]:
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
        stock: dict[str, float] = {}
        for row in self._get(f"'{STOCK_SHEET}'!A2:B"):
            if len(row) >= 2 and isinstance(row[1], (int, float)):
                stock[normalize_model(str(row[0]))] = float(row[1])
        return wholesale, support, stock

    def _current_rows(self) -> list[list[Any]]:
        return self._get(f"'{CURRENT_SHEET}'!A2:R")

    def _latest_manual_values(self) -> dict[str, tuple[Any, Any]]:
        latest: dict[str, tuple[Any, Any]] = {}
        for row in self._get(f"'{HISTORY_SHEET}'!B2:K"):
            if not row:
                continue
            model = normalize_model(str(row[0]))
            manual_last = row[8] if len(row) > 8 else ""
            manual_last_date = row[9] if len(row) > 9 else ""
            latest[model] = (manual_last, manual_last_date)
        for row in self._get(f"'{MANUAL_ARCHIVE_SHEET}'!A2:C"):
            if not row:
                continue
            model = normalize_model(str(row[0]))
            manual_last = row[1] if len(row) > 1 else ""
            manual_last_date = row[2] if len(row) > 2 else ""
            latest[model] = (manual_last, manual_last_date)
        return latest

    def _update_manual_archive(
        self,
        old_rows: list[list[Any]],
        historical_manual: dict[str, tuple[Any, Any]],
        now: str,
    ) -> None:
        archive = dict(historical_manual)
        for row in old_rows:
            if not row:
                continue
            model = normalize_model(str(row[0]))
            manual_last = row[8] if len(row) > 8 else ""
            manual_last_date = row[9] if len(row) > 9 else ""
            if manual_last != "" or manual_last_date != "":
                archive[model] = (manual_last, manual_last_date)

        rows = [[model, values[0], values[1], now] for model, values in sorted(archive.items())]
        self.values.clear(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{MANUAL_ARCHIVE_SHEET}'!A2:D",
        ).execute()
        if rows:
            self.values.update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{MANUAL_ARCHIVE_SHEET}'!A2:D{len(rows)+1}",
                valueInputOption="USER_ENTERED",
                body={"values": rows},
            ).execute()

    def write_current_and_history(
        self,
        products: list[ProductPrice],
        wholesale: dict[str, ReferenceValue],
        support: dict[str, ReferenceValue],
        stock: dict[str, float],
    ) -> dict[str, Any]:
        old_rows = self._current_rows()
        old_by_model = {normalize_model(str(row[0])): row for row in old_rows if row}
        historical_manual = self._latest_manual_values()
        now = datetime.now(ISTANBUL).strftime("%Y-%m-%d %H:%M:%S")
        self._update_manual_archive(old_rows, historical_manual, now)
        rows: list[list[Any]] = []
        history_rows: list[list[Any]] = []
        changed: list[dict[str, Any]] = []
        new_models: list[str] = []
        seen: set[str] = set()

        sorted_products = sorted(
            products,
            key=lambda product: (
                -stock.get(product.model, 0),
                product.category,
                product.model,
            ),
        )

        for product in sorted_products:
            model = product.model
            seen.add(model)
            old = old_by_model.get(model, [])
            historical_last, historical_last_date = historical_manual.get(model, ("", ""))
            manual_last = old[8] if old and len(old) > 8 else historical_last
            manual_last_date = old[9] if old and len(old) > 9 else historical_last_date
            wholesale_value = wholesale.get(model)
            support_value = support.get(model)
            stock_cell: Any = stock.get(model, 0 if stock else "")
            wholesale_cell: Any = wholesale_value.amount if wholesale_value else "Üretimden Kalktı"
            support_cell: Any = support_value.amount if support_value else "YOK"
            bosch_price: Any = product.bosch_price if product.bosch_price is not None else "YOK"
            mediamarkt_price: Any = product.mediamarkt_price if product.mediamarkt_price is not None else "YOK"
            support_amount = support_value.amount if support_value else 0.0
            net_wholesale_value: Any = wholesale_value.amount - support_amount if wholesale_value else "Üretimden Kalktı"
            manual_last_number = as_float(manual_last)
            net_last_value: Any = manual_last_number - support_amount if manual_last_number is not None else ""
            net_wholesale_profitability: Any = ""
            if (
                product.mediamarkt_price is not None
                and isinstance(net_wholesale_value, (int, float))
                and net_wholesale_value != 0
            ):
                net_wholesale_profitability = (product.mediamarkt_price - net_wholesale_value) / net_wholesale_value
            net_last_profitability: Any = ""
            if product.mediamarkt_price is not None and isinstance(net_last_value, (int, float)) and net_last_value != 0:
                net_last_profitability = (product.mediamarkt_price - net_last_value) / net_last_value
            row_number = len(rows) + 2
            net_wholesale = (
                f'=IF(H{row_number}="Üretimden Kalktı";"Üretimden Kalktı";'
                f'H{row_number}-IF(ISNUMBER(K{row_number});K{row_number};0))'
            )
            net_wholesale_profit = (
                f'=IF(OR(NOT(ISNUMBER(L{row_number}));L{row_number}=0);"";'
                f'(C{row_number}-L{row_number})/L{row_number})'
            )
            net_last = f'=IF(I{row_number}="";"";I{row_number}-IF(ISNUMBER(K{row_number});K{row_number};0))'
            net_last_profit = (
                f'=IF(OR(NOT(ISNUMBER(N{row_number}));N{row_number}=0);"";'
                f'(C{row_number}-N{row_number})/N{row_number})'
            )
            row = [
                model,
                product.category,
                mediamarkt_price,
                product.mediamarkt_espark_stock,
                product.mediamarkt_vega_stock,
                bosch_price,
                stock_cell,
                wholesale_cell,
                manual_last,
                manual_last_date,
                support_cell,
                net_wholesale,
                net_wholesale_profit,
                net_last,
                net_last_profit,
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
                    product.mediamarkt_espark_stock,
                    product.mediamarkt_vega_stock,
                    bosch_price,
                    stock_cell,
                    wholesale_cell,
                    manual_last,
                    manual_last_date,
                    support_cell,
                    net_wholesale_value,
                    net_wholesale_profitability,
                    net_last_value,
                    net_last_profitability,
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

        self.values.clear(spreadsheetId=self.spreadsheet_id, range=f"'{CURRENT_SHEET}'!A2:R").execute()
        if rows:
            self.values.update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{CURRENT_SHEET}'!A2:R{len(rows)+1}",
                valueInputOption="USER_ENTERED",
                body={"values": rows},
            ).execute()
        if history_rows:
            self.values.append(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{HISTORY_SHEET}'!A:R",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": history_rows},
            ).execute()
        return {
            "checked": len(sorted_products),
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
