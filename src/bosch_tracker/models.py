from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ProductPrice:
    model: str
    category: str
    mediamarkt_price: float | None
    mediamarkt_url: str
    mediamarkt_stock: str
    mediamarkt_seller: str
    mediamarkt_espark_stock: str = "KONTROL EDİLEMEDİ"
    mediamarkt_vega_stock: str = "KONTROL EDİLEMEDİ"
    bosch_price: float | None = None
    bosch_url: str = ""
    bosch_status: str = "Kontrol edilmedi"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReferenceValue:
    model: str
    amount: float
    source_type: str
    period: str = ""
    source_file: str = ""
