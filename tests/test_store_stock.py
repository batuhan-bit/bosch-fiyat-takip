import json
from urllib.parse import parse_qs, urlsplit

from bosch_tracker.models import ProductPrice
from bosch_tracker.store_stock import (
    STORE_STOCK_OPERATION,
    STORE_STOCK_QUERY_HASH,
    build_store_stock_url,
    enrich_store_stock,
    extract_product_id,
    parse_store_stock,
)


def _product() -> ProductPrice:
    return ProductPrice(
        model="SMI4IKB50T",
        category="Bulaşık Makinesi",
        mediamarkt_price=30_000,
        mediamarkt_url=(
            "https://www.mediamarkt.com.tr/tr/product/"
            "_bosch-smi4ikb50t-bulasik-makinesi-1239150.html"
        ),
        mediamarkt_stock="Stokta",
        mediamarkt_seller="MediaMarkt",
    )


def test_store_stock_url_uses_official_persisted_query_for_eskisehir() -> None:
    assert extract_product_id(_product().mediamarkt_url) == "1239150"

    query = parse_qs(urlsplit(build_store_stock_url("1239150")).query)
    variables = json.loads(query["variables"][0])
    extensions = json.loads(query["extensions"][0])

    assert query["operationName"] == [STORE_STOCK_OPERATION]
    assert variables["zipCodeOrCity"] == "Eskişehir"
    assert variables["productId"] == "1239150"
    assert extensions["persistedQuery"]["sha256Hash"] == STORE_STOCK_QUERY_HASH


def test_store_stock_parser_maps_espark_and_vega() -> None:
    payload = {
        "data": {
            "closestStoresWithFoundLocation": {
                "stores": [
                    {
                        "id": "196",
                        "cofrProductAggregate": {
                            "cofrPickupFeature": {"pickupStatus": "AVAILABLE_LATER_TODAY"}
                        },
                    },
                    {
                        "id": "1970",
                        "cofrProductAggregate": {
                            "cofrPickupFeature": {"pickupStatus": "NOT_AVAILABLE"}
                        },
                    },
                ]
            }
        }
    }

    assert parse_store_stock(payload) == {"espark": "VAR", "vega": "YOK"}


def test_missing_store_data_is_not_reported_as_out_of_stock() -> None:
    assert parse_store_stock({"data": {}}) == {
        "espark": "KONTROL EDİLEMEDİ",
        "vega": "KONTROL EDİLEMEDİ",
    }


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class _Client:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.url = ""

    def get(self, url: str) -> _Response:
        self.url = url
        return _Response(self.payload)


def test_product_is_enriched_with_both_store_results() -> None:
    payload = {
        "data": {
            "closestStoresWithFoundLocation": {
                "stores": [
                    {
                        "id": "196",
                        "cofrProductAggregate": {
                            "cofrPickupFeature": {"pickupStatus": "AVAILABLE_TOMORROW"}
                        },
                    },
                    {
                        "id": "1970",
                        "cofrProductAggregate": {
                            "cofrPickupFeature": {"pickupStatus": "AVAILABLE_WITHIN_THIRTY_MINUTES"}
                        },
                    },
                ]
            }
        }
    }
    product = _product()
    client = _Client(payload)

    enrich_store_stock(product, client)

    assert product.mediamarkt_espark_stock == "VAR"
    assert product.mediamarkt_vega_stock == "VAR"
    assert "productId%22%3A%221239150%22" in client.url
