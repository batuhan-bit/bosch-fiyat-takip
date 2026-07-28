from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import urlencode

from .http_client import PoliteHttpClient
from .models import ProductPrice


STORE_STOCK_ENDPOINT = "https://www.mediamarkt.com.tr/api/v1/graphql"
STORE_STOCK_OPERATION = "GetClosestStoresByZipCodeOrCityWithFoundLocation"
STORE_STOCK_QUERY_HASH = "aed000a926d7a91ed636bfbde453059505a83dc3bc1f54dc7e26f5355a5b6c35"
STORE_IDS = {
    "espark": "196",
    "vega": "1970",
}
AVAILABLE_PICKUP_STATUSES = {
    "AVAILABLE_WITHIN_THIRTY_MINUTES",
    "AVAILABLE_LATER_TODAY",
    "AVAILABLE_TOMORROW",
    "AVAILABLE_WITHIN_REASONABLE_TIMEFRAME",
    "AVAILABLE_OUTSIDE_REASONABLE_TIMEFRAME",
}
UNKNOWN = "KONTROL EDİLEMEDİ"

COFR_CONFIG: dict[str, Any] = {
    "isEnabled": True,
    "baseDomain": "https://www.mediamarkt.com.tr",
    "channel": "DESKTOP",
    "isLegacyDataExcluded": False,
    "features": {
        "badges": {"isFreeShippingBadgeIncluded": False},
        "crossSalesLine": {"isEnabled": False, "isOutputForced": False},
        "onlineStatus": {"isPermanentlyNaIndexEnabled": True},
        "pickup": {"isStrictPickupDisplayStatusEnabled": False},
        "price": {
            "strikePriceTypes": [
                {"strikePriceType": "lop"},
                {
                    "strikePriceType": "rrp",
                    "shouldBeStruck": False,
                    "showDiscountBadge": False,
                    "isLegalTextInlineAllowed": False,
                },
            ],
            "isBasePriceRequiredFlagRespected": False,
            "isDiscountLabelEnabled": True,
            "isDiscountPercentageShown": True,
            "isDisplayPriceWithStrikePriceRrpThemed": True,
            "isLongerStrikePricePrefixAllowed": False,
            "isPromoPriceFiltered": True,
            "isPromoPriceUsedAsDisplayPriceInApp": False,
            "isHistoryChartEnabled": False,
            "discountPercentageMinimum": 5,
            "discountPercentageMinimumFractionDigits": 2,
        },
        "delivery": {
            "isDeliveryStatusByEarliestDateEnabled": True,
            "isLocationSourcingEnabled": False,
            "isLocationSourcingMarketplaceEnabled": False,
        },
        "refurbishedGoods": {"isEnabled": True},
    },
    "client": {},
}

PWA_CONTEXT = {
    "captureChannel": "DESKTOP",
    "salesLine": "Media",
    "country": "TR",
    "language": "tr",
    "globalLoyaltyProgram": True,
    "isOneAccountProgramActive": True,
    "isCustomerReturnApiActive": True,
    "isUsingXccCustomerComponent": True,
    "isCheckoutAptNrActive": True,
    "isCheckoutAddressLevelActive": True,
    "isCheckoutAddressDistrictActive": True,
    "isCheckoutAddressQuarterActive": True,
    "isCheckoutPhoneCompareActive": True,
}


def extract_product_id(product_url: str) -> str | None:
    match = re.search(r"-(\d+)\.html(?:[?#].*)?$", product_url)
    return match.group(1) if match else None


def build_store_stock_url(product_id: str) -> str:
    variables = {
        "limit": 30,
        "withDeliveryPromise": False,
        "zipCodeOrCity": "Eskişehir",
        "productId": product_id,
        "config": COFR_CONFIG,
    }
    extensions = {
        "persistedQuery": {"version": 1, "sha256Hash": STORE_STOCK_QUERY_HASH},
        "pwa": PWA_CONTEXT,
    }
    query = urlencode(
        {
            "operationName": STORE_STOCK_OPERATION,
            "variables": json.dumps(variables, ensure_ascii=False, separators=(",", ":")),
            "extensions": json.dumps(extensions, ensure_ascii=False, separators=(",", ":")),
        }
    )
    return f"{STORE_STOCK_ENDPOINT}?{query}"


def parse_store_stock(payload: dict[str, Any]) -> dict[str, str]:
    result = {"espark": UNKNOWN, "vega": UNKNOWN}
    stores = payload.get("data", {}).get("closestStoresWithFoundLocation", {}).get("stores", [])
    if not isinstance(stores, list):
        return result

    keys_by_store_id = {store_id: key for key, store_id in STORE_IDS.items()}
    for store in stores:
        if not isinstance(store, dict):
            continue
        key = keys_by_store_id.get(str(store.get("id", "")))
        if not key:
            continue
        aggregate = store.get("cofrProductAggregate") or {}
        feature = (aggregate.get("cofrPickupFeature") or {}) if isinstance(aggregate, dict) else {}
        status = str(feature.get("pickupStatus", "")) if isinstance(feature, dict) else ""
        if status:
            result[key] = "VAR" if status in AVAILABLE_PICKUP_STATUSES else "YOK"
    return result


def enrich_store_stock(product: ProductPrice, client: PoliteHttpClient) -> None:
    product_id = extract_product_id(product.mediamarkt_url)
    if not product_id:
        return
    try:
        response = client.get(build_store_stock_url(product_id))
        response.raise_for_status()
        payload = response.json()
        if os.getenv("DEBUG_STORE_STOCK", "").casefold() in {"1", "true", "yes"}:
            print(json.dumps({"product_id": product_id, "payload": payload}, ensure_ascii=False))
        stock = parse_store_stock(payload)
    except Exception as exc:
        if os.getenv("DEBUG_STORE_STOCK", "").casefold() in {"1", "true", "yes"}:
            status_code = getattr(locals().get("response"), "status_code", None)
            response_text = getattr(locals().get("response"), "text", "")
            print(
                json.dumps(
                    {
                        "product_id": product_id,
                        "status_code": status_code,
                        "error": str(exc),
                        "response": str(response_text)[:1000],
                    },
                    ensure_ascii=False,
                )
            )
        return
    product.mediamarkt_espark_stock = stock["espark"]
    product.mediamarkt_vega_stock = stock["vega"]
