from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class RateLimitError(Exception):
    def __init__(self, retry_after_seconds: Optional[float] = None) -> None:
        super().__init__("Finnhub rate limit reached")
        self.retry_after_seconds = retry_after_seconds


class FinnhubClient:
    BASE_URL = "https://finnhub.io/api/v1/quote"

    def __init__(self, api_key: str, timeout_seconds: int = 10) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
        reraise=True,
    )
    def fetch_quote(self, symbol: str) -> dict[str, Any]:
        response = requests.get(
            self.BASE_URL,
            params={"symbol": symbol, "token": self.api_key},
            timeout=self.timeout_seconds,
        )
        if response.status_code == 429:
            retry_after_raw = response.headers.get("Retry-After")
            retry_after_seconds = float(retry_after_raw) if retry_after_raw else None
            raise RateLimitError(retry_after_seconds=retry_after_seconds)

        response.raise_for_status()
        payload = response.json()

        return {
            "symbol": symbol,
            "price_current": payload.get("c"),
            "price_high": payload.get("h"),
            "price_low": payload.get("l"),
            "price_open": payload.get("o"),
            "price_previous_close": payload.get("pc"),
            "finnhub_timestamp": payload.get("t"),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "source": "finnhub",
        }
