"""Simulateur de flux temps réel — mode démo (marché fermé).

Génère des cotations qui bougent (marche aléatoire à partir des derniers prix réels)
et les publie sur Kafka exactement comme le ferait le Producer. Le Consumer les traite,
et le dashboard s'affiche en LIVE avec des prix qui évoluent — même hors heures de marché.

Usage : PYTHONPATH=src python scripts/replay_simulator.py
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from producer.kafka_sink import KafkaQuoteSink
from producer.csv_sink import CsvQuoteSink

SYMBOLS = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
TOPIC = os.getenv("KAFKA_TOPIC", "market.quotes.raw")
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BACKUP_CSV = os.getenv("BACKUP_CSV_PATH", "data/quotes_backup.csv")
HISTORY_DIR = Path("data/history")


def _base_prices() -> dict[str, float]:
    prices: dict[str, float] = {}
    for s in SYMBOLS:
        p = HISTORY_DIR / f"{s}_1d.parquet"
        prices[s] = float(pd.read_parquet(p)["Close"].iloc[-1]) if p.exists() else 100.0
    return prices


def main() -> None:
    ap = argparse.ArgumentParser(description="Simulateur de flux (mode démo).")
    ap.add_argument("--target", choices=["kafka", "csv"], default="kafka",
                    help="kafka = flux live (Producer→Kafka) ; csv = alimente le backup (démo FALLBACK)")
    ap.add_argument("--interval", type=float, default=0.4, help="secondes entre chaque tick")
    args = ap.parse_args()

    if args.target == "kafka":
        _sink = KafkaQuoteSink(bootstrap_servers=BOOTSTRAP, client_id="replay-simulator")
        emit = lambda q: _sink.publish(TOPIC, q["symbol"], q)
        flush = _sink.flush
        print(f"[simulateur] mode KAFKA (flux live) · {len(SYMBOLS)} symboles (Ctrl+C pour arrêter)")
    else:
        _sink = CsvQuoteSink(BACKUP_CSV)
        emit = _sink.write
        flush = lambda: None
        print(f"[simulateur] mode CSV → {BACKUP_CSV} (démo FALLBACK) · {len(SYMBOLS)} symboles (Ctrl+C)")

    prices = _base_prices()
    prev_close = dict(prices)
    try:
        while True:
            for s in SYMBOLS:
                drift = random.gauss(0, 0.0018)          # ~0.18% d'écart-type par tick
                prices[s] = max(1.0, prices[s] * (1 + drift))
                cur = round(prices[s], 2)
                quote = {
                    "symbol": s,
                    "price_current": cur,
                    "price_high": round(cur * (1 + abs(random.gauss(0, 0.001))), 2),
                    "price_low": round(cur * (1 - abs(random.gauss(0, 0.001))), 2),
                    "price_open": round(prev_close[s], 2),
                    "price_previous_close": round(prev_close[s], 2),
                    "finnhub_timestamp": int(time.time()),
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "source": "simulator",
                }
                emit(quote)
                time.sleep(args.interval)
            flush()
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[simulateur] arrêté.")


if __name__ == "__main__":
    main()
