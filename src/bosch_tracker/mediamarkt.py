from __future__ import annotations

import os
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

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


def parse_sellable_category_products(html: str, category: str, base_url: str) -> list[ProductPrice]:
    listed = parse_category_products(html)
    prices_by_url: dict[str, float] = {}
    for item in listed:
        url = urljoin(base_url, str(item.get("url", "")))
        price = as_float(first_offer(item.get("offers")).get("price"))
        if url and price is not None:
            prices_by_url[url] = price

    soup = BeautifulSoup(html, "html.parser")
    products: list[ProductPrice] = []
    for card in soup.select('article[data-test="mms-product-card"]'):
        link = card.select_one('a[data-test="mms-router-link-product-list-item-link"]')
        title = card.select_one('[data-test="product-title"]')
        if not link or not title:
            continue
        name = title.get_text(" ", strip=True)
        if not name.upper().startswith("BOSCH"):
            continue
        model = extract_model(name)
        if not model:
            continue

        # Pazaryeri ürünleri kart üzerinde sağlayıcı bağlantısıyla işaretlenir.
        if card.select_one('[data-test="mms-third-party-provider-link"]'):
            continue
        basket_buttons = card.select('[data-test*="cofr-add-to-basket-button"]')
        if not any(
            button.get("aria-disabled", "false").casefold() != "true" and not button.has_attr("disabled")
            for button in basket_buttons
        ):
            continue

        product_url = urljoin(base_url, str(link.get("href", "")))
        price = prices_by_url.get(product_url)
        if price is None:
            continue
        products.append(
            ProductPrice(
                model=model,
                category=category,
                mediamarkt_price=price,
                mediamarkt_url=product_url,
                mediamarkt_stock="Stokta",
                mediamarkt_seller="MediaMarkt",
            )
        )
    return products


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
        seen_listing_urls: set[str] = set()
        seen_models: set[str] = set()
        for category, category_url in MEDIAMARKT_CATEGORIES.items():
            for page in range(1, self.max_pages + 1):
                response = self.client.get(_with_page(category_url, page))
                response.raise_for_status()
                listed = parse_category_products(response.text)
                listed_urls = {
                    urljoin(response.url, str(item.get("url", "")))
                    for item in listed
                    if item.get("url")
                }
                new_listing_urls = listed_urls - seen_listing_urls
                if not listed or not new_listing_urls:
                    break
                seen_listing_urls.update(new_listing_urls)

                for product in parse_sellable_category_products(response.text, category, response.url):
                    if product.model in seen_models:
                        continue
                    seen_models.add(product.model)
                    products.append(product)
                    if max_products and len(products) >= max_products:
                        products.sort(key=lambda item: (item.category, item.model))
                        return products
        products.sort(key=lambda item: (item.category, item.model))
        return products
