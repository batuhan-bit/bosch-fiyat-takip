from types import SimpleNamespace

from bosch_tracker.http_client import PoliteHttpClient


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str, **kwargs: object) -> SimpleNamespace:
        self.calls.append((url, kwargs))
        return SimpleNamespace(status_code=200)


def test_proxy_is_used_only_for_mediamarkt(monkeypatch) -> None:
    proxy_url = "http://user:pass@gate.decodo.com:7000"
    monkeypatch.setenv("MEDIAMARKT_PROXY_URL", proxy_url)
    monkeypatch.setenv("REQUEST_DELAY_SECONDS", "0")
    client = PoliteHttpClient()
    fake_session = FakeSession()
    client.session = fake_session

    client.get("https://www.mediamarkt.com.tr/tr/category/example")
    client.get("https://www.bosch-home.com.tr/tr/product/example")

    assert fake_session.calls[0][1]["proxy"] == proxy_url
    assert "proxy" not in fake_session.calls[1][1]
