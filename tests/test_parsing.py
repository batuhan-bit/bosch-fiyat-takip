from bosch_tracker.mediamarkt import parse_category_products, parse_product_page, parse_sellable_category_products
from bosch_tracker.parsing import extract_model, normalize_model


def test_model_normalization() -> None:
    assert normalize_model("wgk-242z0tr") == "WGK242Z0TR"
    assert extract_model("BOSCH Serie 6 WGK242Z0TR Çamaşır Makinesi") == "WGK242Z0TR"


def test_category_json_ld() -> None:
    html = '''
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"ItemList","itemListElement":[
      {"@type":"ListItem","item":{"@type":"Product","name":"BOSCH WGK242Z0TR Makine","url":"https://www.mediamarkt.com.tr/p/1"}}
    ]}
    </script>
    '''
    assert parse_category_products(html)[0]["name"].startswith("BOSCH")


def test_sellable_mediamarkt_product_is_read_from_category_card() -> None:
    html = """
    <script type="application/ld+json">
    {"@type":"ItemList","itemListElement":[
      {"item":{"@type":"Product","name":"BOSCH WGK242Z0TR Makine","url":"/tr/product/bosch-1.html","offers":{"@type":"Offer","price":36999}}}
    ]}
    </script>
    <article data-test="mms-product-card">
      <a data-test="mms-router-link-product-list-item-link" href="/tr/product/bosch-1.html">
        <p data-test="product-title">BOSCH WGK242Z0TR Çamaşır Makinesi</p>
      </a>
      <button data-test="cofr-add-to-basket-button a2c-Button" aria-disabled="false">Sepete Ekle</button>
    </article>
    """
    products = parse_sellable_category_products(html, "Çamaşır Makinesi", "https://www.mediamarkt.com.tr/list")
    assert len(products) == 1
    assert products[0].model == "WGK242Z0TR"
    assert products[0].mediamarkt_price == 36999


def test_marketplace_and_unavailable_category_cards_are_rejected() -> None:
    html = """
    <script type="application/ld+json">
    {"@type":"ItemList","itemListElement":[
      {"item":{"@type":"Product","name":"BOSCH WGK242Z0TR Makine","url":"/tr/product/marketplace.html","offers":{"price":30000}}},
      {"item":{"@type":"Product","name":"BOSCH WQG24100TR Kurutma","url":"/tr/product/unavailable.html","offers":{"price":31000}}}
    ]}
    </script>
    <article data-test="mms-product-card">
      <a data-test="mms-router-link-product-list-item-link" href="/tr/product/marketplace.html"><p data-test="product-title">BOSCH WGK242Z0TR Makine</p></a>
      <a data-test="mms-third-party-provider-link">Başka satıcı</a>
      <button data-test="cofr-add-to-basket-button" aria-disabled="false">Sepete Ekle</button>
    </article>
    <article data-test="mms-product-card">
      <a data-test="mms-router-link-product-list-item-link" href="/tr/product/unavailable.html"><p data-test="product-title">BOSCH WQG24100TR Kurutma</p></a>
      <button data-test="cofr-add-to-basket-button" aria-disabled="true">Stokta yok</button>
    </article>
    """
    assert parse_sellable_category_products(html, "Beyaz Eşya", "https://www.mediamarkt.com.tr/list") == []


def test_mediamarkt_owned_product() -> None:
    html = '''
    <script type="application/ld+json">
    {"@context":"https://schema.org/","@type":"BuyAction","object":{"@type":"Product","brand":{"@type":"Brand","name":"BOSCH"},"name":"BOSCH WGK242Z0TR Çamaşır Makinesi","url":"https://www.mediamarkt.com.tr/p/1","offers":{"@type":"Offer","price":36999,"availability":"https://schema.org/InStock"}}}
    </script>
    '''
    product = parse_product_page(html, "https://www.mediamarkt.com.tr/p/1", "Çamaşır Makinesi")
    assert product is not None
    assert product.mediamarkt_seller == "MediaMarkt"
    assert product.mediamarkt_price == 36999


def test_marketplace_product_is_rejected() -> None:
    html = '''
    <script type="application/ld+json">
    {"@context":"https://schema.org/","@type":"BuyAction","object":{"@type":"Product","brand":{"@type":"Brand","name":"BOSCH"},"name":"BOSCH WGK242Z0TR Çamaşır Makinesi","offers":{"@type":"Offer","price":40000,"availability":"https://schema.org/InStock"}}}
    </script>
    <a data-test="mms-third-party-provider-link">RAST ENTERPRISE</a>
    '''
    assert parse_product_page(html, "https://www.mediamarkt.com.tr/p/2", "Çamaşır Makinesi") is None


def test_out_of_stock_product_is_rejected() -> None:
    html = '''
    <script type="application/ld+json">
    {"@context":"https://schema.org/","@type":"BuyAction","object":{"@type":"Product","brand":{"@type":"Brand","name":"BOSCH"},"name":"BOSCH WGK242Z0TR Çamaşır Makinesi","offers":{"@type":"Offer","price":36999,"availability":"https://schema.org/OutOfStock"}}}
    </script>
    '''
    assert parse_product_page(html, "https://www.mediamarkt.com.tr/p/4", "Çamaşır Makinesi") is None


def test_non_bosch_sponsored_product_is_rejected() -> None:
    html = '''
    <script type="application/ld+json">
    {"@context":"https://schema.org/","@type":"BuyAction","object":{"@type":"Product","brand":{"@type":"Brand","name":"SIEMENS"},"name":"SIEMENS SN23EW63KT Bulaşık Makinesi","offers":{"@type":"Offer","price":30000}}}
    </script>
    '''
    assert parse_product_page(html, "https://www.mediamarkt.com.tr/p/3", "Bulaşık Makinesi") is None
