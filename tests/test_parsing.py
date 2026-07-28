from bosch_tracker.mediamarkt import parse_category_products, parse_product_page
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
