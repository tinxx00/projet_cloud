from __future__ import annotations

from datetime import datetime, timezone
from typing import Any



def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None



def process_quote(raw_quote: dict[str, Any], ingestion_mode: str) -> dict[str, Any]:
    current = _to_float(raw_quote.get("price_current"))
    previous_close = _to_float(raw_quote.get("price_previous_close"))

    delta_abs = None
    delta_pct = None
    direction = "unknown"

    if current is not None and previous_close is not None:
        delta_abs = current - previous_close
        if previous_close != 0:
            delta_pct = (delta_abs / previous_close) * 100

        if delta_abs > 0:
            direction = "up"
        elif delta_abs < 0:
            direction = "down"
        else:
            direction = "flat"

    return {
        "symbol": raw_quote.get("symbol"),
        "price_current": current,
        "price_high": _to_float(raw_quote.get("price_high")),
        "price_low": _to_float(raw_quote.get("price_low")),
        "price_open": _to_float(raw_quote.get("price_open")),
        "price_previous_close": previous_close,
        "finnhub_timestamp": raw_quote.get("finnhub_timestamp"),
        "ingested_at": raw_quote.get("ingested_at"),
        "source": raw_quote.get("source", "finnhub"),
        "ingestion_mode": ingestion_mode,
        "delta_abs": delta_abs,
        "delta_pct": delta_pct,
        "direction": direction,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
