from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlsplit

from curl_cffi import requests


class PoliteHttpClient:
    def __init__(self) -> None:
        self.delay = float(os.getenv("REQUEST_DELAY_SECONDS", "0.6"))
        self.timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
        self.mediamarkt_proxy = os.getenv("MEDIAMARKT_PROXY_URL", "").strip()
        # MediaMarkt, standart Python TLS imzasını otomasyon olarak engelleyebiliyor.
        # curl_cffi doğrudan resmi siteye bağlanırken güncel Chrome ağ imzasını kullanır.
        self.session = requests.Session(impersonate="chrome")
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self._last_request = 0.0

    def get(self, url: str) -> Any:
        response: Any = None
        hostname = (urlsplit(url).hostname or "").casefold()
        use_mediamarkt_proxy = bool(self.mediamarkt_proxy) and (
            hostname == "mediamarkt.com.tr" or hostname.endswith(".mediamarkt.com.tr")
        )
        for attempt in range(4):
            elapsed = time.monotonic() - self._last_request
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            request_options: dict[str, Any] = {}
            if use_mediamarkt_proxy:
                request_options["proxy"] = self.mediamarkt_proxy
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                **request_options,
            )
            self._last_request = time.monotonic()
            if response.status_code not in (429, 500, 502, 503, 504):
                return response
            if attempt < 3:
                time.sleep(2**attempt)
        return response
