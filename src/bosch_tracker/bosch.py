from __future__ import annotations

from .http_client import PoliteHttpClient
from .models import ProductPrice
from .parsing import as_float, first_offer, json_ld_objects, normalize_model, schema_type


BOSCH_PRODUCT_URL = "https://www.bosch-home.com.tr/tr/product/{model}"


def enrich_from_bosch(product: ProductPrice, client: PoliteHttpClient) -> None:
    url = BOSCH_PRODUCT_URL.format(model=product.model)
    response = client.get(url)
    if response.status_code == 404:
        product.bosch_url = url
        product.bosch_status = "Bosch sitesinde bulunamadı"
        return
    response.raise_for_status()

    for value in json_ld_objects(response.text):
        if "Product" not in schema_type(value):
            continue
        model = normalize_model(str(value.get("mpn", "")))
        if model != product.model:
            continue
        offer = first_offer(value.get("offers"))
        availability = str(offer.get("availability", ""))
        product.bosch_price = as_float(offer.get("price"))
        product.bosch_url = str(value.get("@id") or offer.get("url") or response.url)
        if product.bosch_price is None:
            product.bosch_status = "Ürün var, satış fiyatı yok"
        elif availability.endswith("InStock"):
            product.bosch_status = "Stokta"
        else:
            product.bosch_status = "Stokta yok"
        return

    product.bosch_url = response.url
    product.bosch_status = "Bosch sitesinde bulunamadı"

