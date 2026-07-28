from bosch_tracker.google_sheets import GoogleSheetsClient
from bosch_tracker.models import ProductPrice, ReferenceValue


class _Request:
    def __init__(self, response=None):
        self.response = response or {}

    def execute(self):
        return self.response


class _Values:
    def __init__(self, current_rows, history_rows=None):
        self.current_rows = current_rows
        self.history_rows = history_rows or []
        self.updates = []
        self.appends = []
        self.clears = []

    def get(self, **kwargs):
        if kwargs["range"] == "'Güncel Fiyatlar'!A2:P":
            return _Request({"values": self.current_rows})
        if kwargs["range"] == "'Fiyat Geçmişi'!B2:I":
            return _Request({"values": self.history_rows})
        raise AssertionError(kwargs["range"])

    def clear(self, **kwargs):
        self.clears.append(kwargs)
        return _Request()

    def update(self, **kwargs):
        self.updates.append(kwargs)
        return _Request()

    def append(self, **kwargs):
        self.appends.append(kwargs)
        return _Request()


def test_manual_last_purchase_price_and_date_are_preserved():
    existing = [
        "WGG244Z0TR",
        "Çamaşır Makinesi",
        30_000,
        32_000,
        8,
        25_000,
        24_000,
        "15.07.2026",
        1_000,
        24_000,
        0.25,
        23_000,
        0.30,
        "2026-07-27 09:00:00",
        "https://www.mediamarkt.com.tr/example",
        "https://www.bosch-home.com.tr/example",
    ]
    values = _Values([existing])
    client = GoogleSheetsClient.__new__(GoogleSheetsClient)
    client.spreadsheet_id = "sheet-id"
    client.values = values

    product = ProductPrice(
        model="WGG244Z0TR",
        category="Çamaşır Makinesi",
        mediamarkt_price=29_500,
        mediamarkt_url="https://www.mediamarkt.com.tr/example",
        mediamarkt_stock="Stokta",
        mediamarkt_seller="MediaMarkt",
        bosch_price=32_000,
        bosch_url="https://www.bosch-home.com.tr/example",
        bosch_status="Bosch'ta bulundu",
    )
    wholesale = {"WGG244Z0TR": ReferenceValue("WGG244Z0TR", 25_000, "Toptan")}
    support = {"WGG244Z0TR": ReferenceValue("WGG244Z0TR", 1_000, "BSP")}

    client.write_current_and_history([product], wholesale, support, {"WGG244Z0TR": 6})

    current_row = values.updates[0]["body"]["values"][0]
    history_row = values.appends[0]["body"]["values"][0]
    assert len(current_row) == 16
    assert current_row[4:9] == [6, 25_000, 24_000, "15.07.2026", 1_000]
    assert "ISNUMBER(I2)" in current_row[9]
    assert "(C2-J2)/J2" in current_row[10]
    assert "ISNUMBER(I2)" in current_row[11]
    assert "(C2-L2)/L2" in current_row[12]
    assert len(history_row) == 16
    assert history_row[5:10] == [6, 25_000, 24_000, "15.07.2026", 1_000]
    assert history_row[11] == (29_500 - 24_000) / 24_000
    assert history_row[13] == (29_500 - 23_000) / 23_000
    assert values.clears[0]["range"] == "'Güncel Fiyatlar'!A2:P"
    assert values.updates[0]["range"] == "'Güncel Fiyatlar'!A2:P2"
    assert values.appends[0]["range"] == "'Fiyat Geçmişi'!A:P"


def test_returning_product_recovers_manual_values_from_history():
    historical_manual = [
        ["WGG244Z0TR", "Çamaşır Makinesi", 30_000, 32_000, 8, 25_000, 24_000, "15.07.2026"]
    ]
    values = _Values([], historical_manual)
    client = GoogleSheetsClient.__new__(GoogleSheetsClient)
    client.spreadsheet_id = "sheet-id"
    client.values = values
    product = ProductPrice(
        model="WGG244Z0TR",
        category="Çamaşır Makinesi",
        mediamarkt_price=29_500,
        mediamarkt_url="https://www.mediamarkt.com.tr/example",
        mediamarkt_stock="Stokta",
        mediamarkt_seller="MediaMarkt",
        bosch_price=32_000,
        bosch_url="https://www.bosch-home.com.tr/example",
        bosch_status="Bosch'ta bulundu",
    )

    client.write_current_and_history([product], {}, {}, {})

    current_row = values.updates[0]["body"]["values"][0]
    assert current_row[6:8] == [24_000, "15.07.2026"]
    assert current_row[5] == "Üretimden Kalktı"
    assert "Üretimden Kalktı" in current_row[9]
    assert current_row[10] == '=IF(OR(NOT(ISNUMBER(J2));J2=0);"";(C2-J2)/J2)'


def test_product_that_leaves_stock_is_removed_from_current_sheet():
    existing = [
        "WGG244Z0TR",
        "Çamaşır Makinesi",
        30_000,
        32_000,
        8,
        25_000,
        24_000,
        "15.07.2026",
        1_000,
        24_000,
        0.25,
        23_000,
        0.30,
        "2026-07-27 09:00:00",
        "https://www.mediamarkt.com.tr/example",
        "https://www.bosch-home.com.tr/example",
    ]
    values = _Values([existing])
    client = GoogleSheetsClient.__new__(GoogleSheetsClient)
    client.spreadsheet_id = "sheet-id"
    client.values = values

    summary = client.write_current_and_history([], {}, {}, {})

    assert summary["removed_models"] == ["WGG244Z0TR"]
    assert values.updates == []
    assert values.appends == []
    assert values.clears[0]["range"] == "'Güncel Fiyatlar'!A2:P"
