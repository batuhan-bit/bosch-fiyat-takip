from __future__ import annotations

import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PoliteHttpClient:
    def __init__(self) -> None:
        self.delay = float(os.getenv("REQUEST_DELAY_SECONDS", "0.6"))
        self.timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36 BoschPriceTracker/1.0"
                ),
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
            }
        )
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self._last_request = 0.0

    def get(self, url: str) -> requests.Response:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        self._last_request = time.monotonic()
        return response

