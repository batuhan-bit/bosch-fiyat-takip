from __future__ import annotations

import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .http_client import PoliteHttpClient
from .models import ProductPrice
from .parsing import as_float, extract_model, first_offer, json_ld_objects, schema_type


MEDIAMARKT_CATEGORIES = {
    "Buzdolabı": "https://www.mediamarkt.com.tr/tr/category/bosch-buzdolabi-891522.html",
    "Çamaşır Makinesi": "https://www.mediamarkt.com.tr/tr/category/bosch-camasir-makinesi-891521.html",
    "Kurutma Makinesi": "https://www.mediamarkt.com.tr/tr/category/bosch-kurutma-makinesi-891524.html",
    "Bulaşık Makinesi": "https://www.mediamarkt.com.tr/tr/category/bosch-bulasik-makinesi-891523.html",
}


def _is_mediamarkt_seller(value: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", value.casefold())
    return normalized.startswith("mediamarkt")


def _with_page(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["page"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def parse_category_products(html: str) -> list[dict[str, object]]:
    for value in json_ld_objects(html):
        if "ItemList" not in schema_type(value):
            continue
        products: list[dict[str, object]] = []
        for element in value.get("itemListElement", []):
            if not isinstance(element, dict):
                continue
            item = element.get("item")
            if isinstance(item, dict) and "Product" in schema_type(item):
                products.append(item)
        return products
    return []


def parse_product_page(html: str, fallback_url: str, category: str) -> ProductPrice | None:
    product: dict[str, object] | None = None
    for value in json_ld_objects(html):
        if "BuyAction" in schema_type(value) and isinstance(value.get("object"), dict):
            candidate = value["object"]
            if "Product" in schema_type(candidate):
                product = candidate
                break
    if not product:
        return None

    name = str(product.get("name", ""))
    brand_value = product.get("brand")
    brand_name = str(brand_value.get("name", "")) if isinstance(brand_value, dict) else str(brand_value or "")
    if brand_name and brand_name.strip().upper() != "BOSCH":
        return None
    if not brand_name and not name.strip().upper().startswith("BOSCH"):
        return None
    model = extract_model(name)
    if not model:
        return None

    third_party_marker = 'data-test="mms-third-party-provider-link"' in html
    seller_names = sorted(set(re.findall(r'"sellerName":"([^"\\]+)"', html)))
    if seller_names and not all(_is_mediamarkt_seller(name) for name in seller_names):
        return None
    if third_party_marker and not seller_names:
        return None
    seller = "MediaMarkt"

    offer = first_offer(product.get("offers"))
    availability = str(offer.get("availability", ""))
    price = as_float(offer.get("price"))
    if not availability.endswith("InStock") or price is None:
        return None
    return ProductPrice(
        model=model,
        category=category,
        mediamarkt_price=price,
        mediamarkt_url=str(product.get("url") or fallback_url),
        mediamarkt_stock="Stokta",
        mediamarkt_seller=seller,
    )


class MediaMarktSource:
    def __init__(self, client: PoliteHttpClient) -> None:
        self.client = client
        self.max_pages = int(os.getenv("MEDIAMARKT_MAX_PAGES", "10"))

    def discover(self) -> list[tuple[str, str]]:
        discovered: list[tuple[str, str]] = []
        seen_urls: set[str] = set()
        for category, category_url in MEDIAMARKT_CATEGORIES.items():
            for page in range(1, self.max_pages + 1):
                response = self.client.get(_with_page(category_url, page))
                response.raise_for_status()
                page_items = parse_category_products(response.text)
                new_count = 0
                for item in page_items:
                    url = str(item.get("url", ""))
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        discovered.append((category, url))
                        new_count += 1
                if not page_items or new_count == 0:
                    break
        return discovered

    def fetch_all(self) -> list[ProductPrice]:
        products: list[ProductPrice] = []
        max_products = int(os.getenv("MAX_PRODUCTS", "0"))
        for category, url in self.discover():
            response = self.client.get(url)
            response.raise_for_status()
            product = parse_product_page(response.text, response.url, category)
            if product:
                products.append(product)
                if max_products and len(products) >= max_products:
                    break
        products.sort(key=lambda item: (item.category, item.model))
        return products
