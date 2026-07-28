from bosch_tracker.google_sheets import GoogleSheetsClient
from bosch_tracker.models import ProductPrice, ReferenceValue


class _Request:
    def __init__(self, response=None):
        self.response = response or {}

    def execute(self):
        return self.response


class _Values:
    def __init__(self, current_rows):
        self.current_rows = current_rows
        self.updates = []
        self.appends = []
        self.clears = []

    def get(self, **kwargs):
        assert kwargs["range"] == "'Güncel Fiyatlar'!A2:Q"
        return _Request({"values": self.current_rows})

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
        25_000,
        24_000,
        "15.07.2026",
        1_000,
        24_000,
        23_000,
        "Stokta",
        "Bosch'ta bulundu",
        "Listede",
        "BSP",
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

    client.write_current_and_history([product], wholesale, support)

    current_row = values.updates[0]["body"]["values"][0]
    history_row = values.appends[0]["body"]["values"][0]
    assert len(current_row) == 17
    assert current_row[5:8] == [24_000, "15.07.2026", 1_000]
    assert "ISNUMBER(H2)" in current_row[8]
    assert "ISNUMBER(H2)" in current_row[9]
    assert len(history_row) == 17
    assert history_row[6:9] == [24_000, "15.07.2026", 1_000]
    assert values.clears[0]["range"] == "'Güncel Fiyatlar'!A2:Q"
    assert values.updates[0]["range"] == "'Güncel Fiyatlar'!A2:Q2"
    assert values.appends[0]["range"] == "'Fiyat Geçmişi'!A:Q"
