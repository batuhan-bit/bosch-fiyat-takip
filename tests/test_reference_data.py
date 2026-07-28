from pathlib import Path

from bosch_tracker.reference_data import load_support, load_wholesale


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_uploaded_price_lists() -> None:
    wholesale = load_wholesale(PROJECT_ROOT / "girdiler/toptan-fiyat-listeleri/Bosch Temmuz 2026 TOPTAN.xlsx")
    support = load_support(PROJECT_ROOT / "girdiler/fiyat-farki-listeleri/Bosch Fiyat Fark Tutarları Temmuz 2026.xlsx")
    assert wholesale["WGA242X3TR"].amount > 0
    assert support["WGA242X3TR"].source_type == "BSP"
    assert all(value.source_type != "Aile Bakanlığı" for value in support.values())

