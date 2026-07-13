"""Génère des données de démonstration pour le dashboard, SANS clé API ni Kafka.

Le pipeline temps réel (Finnhub -> Kafka -> Consumer) produit deux fichiers CSV :
  - data/quotes_backup.csv   (cotations brutes du producer)
  - data/processed_quotes.csv (cotations enrichies par le consumer)

Ces fichiers sont ignorés par git (données runtime). Pour qu'un utilisateur
puisse lancer et voir le dashboard rempli immédiatement, ce script reconstruit
ces deux CSV à partir de l'historique déjà versionné (data/history/*_1d.parquet).

Usage :
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --days 90 --symbols AAPL MSFT TSLA
"""
from __future__ import annotations

import argparse
import glob
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HISTORY_DIR = Path("data/history")
RAW_PATH = Path("data/quotes_backup.csv")
PROCESSED_PATH = Path("data/processed_quotes.csv")

RAW_COLS = [
    "symbol", "price_current", "price_high", "price_low", "price_open",
    "price_previous_close", "finnhub_timestamp", "ingested_at", "source",
]
PROCESSED_COLS = RAW_COLS + [
    "ingestion_mode", "delta_abs", "delta_pct", "direction", "processed_at",
]


def _symbols_available() -> list[str]:
    return sorted(
        sym for p in glob.glob(str(HISTORY_DIR / "*_1d.parquet"))
        if (sym := Path(p).stem.replace("_1d", "")) != "TEST"
    )


def _build_rows(symbol: str, days: int) -> list[dict]:
    df = pd.read_parquet(HISTORY_DIR / f"{symbol}_1d.parquet").tail(days)
    if df.empty:
        return []
    df = df.assign(prev_close=df["Close"].shift(1)).dropna(subset=["prev_close"])
    now_iso = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    for ts, r in df.iterrows():
        current = round(float(r["Close"]), 4)
        prev = round(float(r["prev_close"]), 4)
        delta_abs = round(current - prev, 4)
        delta_pct = round((delta_abs / prev) * 100, 4) if prev else 0.0
        direction = "up" if delta_abs > 0 else "down" if delta_abs < 0 else "flat"
        ingested_at = ts.to_pydatetime().astimezone(timezone.utc).isoformat()
        rows.append({
            "symbol": symbol,
            "price_current": current,
            "price_high": round(float(r["High"]), 4),
            "price_low": round(float(r["Low"]), 4),
            "price_open": round(float(r["Open"]), 4),
            "price_previous_close": prev,
            "finnhub_timestamp": int(ts.timestamp()),
            "ingested_at": ingested_at,
            "source": "demo_seed",
            "ingestion_mode": "demo_seed",
            "delta_abs": delta_abs,
            "delta_pct": delta_pct,
            "direction": direction,
            "processed_at": now_iso,
        })
    return rows


def main() -> None:
    available = _symbols_available()
    parser = argparse.ArgumentParser(description="Génère des données démo pour le dashboard.")
    parser.add_argument("--symbols", nargs="+", default=available,
                        help=f"Symboles à inclure (dispo : {', '.join(available) or 'aucun'})")
    parser.add_argument("--days", type=int, default=120,
                        help="Nombre de jours d'historique à charger par symbole (défaut : 120)")
    args = parser.parse_args()

    if not available:
        raise SystemExit(
            "Aucun historique trouvé dans data/history/. "
            "Vérifie que les fichiers *_1d.parquet sont bien présents."
        )

    symbols = [s.upper() for s in args.symbols if s.upper() in available]
    if not symbols:
        raise SystemExit(f"Aucun symbole valide. Disponibles : {', '.join(available)}")

    all_rows: list[dict] = []
    for sym in symbols:
        rows = _build_rows(sym, args.days)
        all_rows.extend(rows)
        print(f"  {sym}: {len(rows)} points")

    if not all_rows:
        raise SystemExit("Aucune donnée générée.")

    df = pd.DataFrame(all_rows).sort_values("ingested_at").reset_index(drop=True)
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)

    # quotes_backup.csv : sans header (format du producer)
    df[RAW_COLS].to_csv(RAW_PATH, index=False, header=False)
    # processed_quotes.csv : avec header (format du consumer)
    df[PROCESSED_COLS].to_csv(PROCESSED_PATH, index=False)

    print(f"\n✅ {len(df)} lignes générées pour {len(symbols)} symboles")
    print(f"   → {RAW_PATH}")
    print(f"   → {PROCESSED_PATH}")
    print("\nLance maintenant :  streamlit run src/dashboard/app.py")


if __name__ == "__main__":
    main()
