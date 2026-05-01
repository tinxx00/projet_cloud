"""Utilitaire de prédiction live, utilisé par le dashboard.

Charge le modèle entraîné une fois (cache), agrège les ticks live du
consumer (`processed_quotes.csv`) en barres OHLC, recalcule les features
et renvoie une probabilité de hausse à l'horizon court terme.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from ml.features import build_features


MODEL_PATH = Path("data/models/direction_model.joblib")


@lru_cache(maxsize=1)
def _load_model_bundle() -> dict | None:
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def model_available() -> bool:
    return MODEL_PATH.exists()


def _ticks_to_bars(df: pd.DataFrame, freq: str = "5min") -> pd.DataFrame:
    """Agrège les ticks (snapshots) en barres OHLCV."""
    if df.empty or "ingested_at" not in df.columns or "price_current" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work["ingested_at"] = pd.to_datetime(work["ingested_at"], errors="coerce", utc=True)
    work = work.dropna(subset=["ingested_at", "price_current"])
    if work.empty:
        return pd.DataFrame()
    work = work.set_index("ingested_at").sort_index()
    bars = work["price_current"].resample(freq).ohlc()
    bars["Volume"] = 0.0
    bars = bars.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"})
    return bars.dropna()


def predict_from_history(history: pd.DataFrame) -> pd.DataFrame:
    """Score un DataFrame OHLCV en sortie ``proba_up`` par barre."""
    bundle = _load_model_bundle()
    if bundle is None or history.empty:
        return pd.DataFrame()
    feats = build_features(history).dropna()
    if feats.empty:
        return pd.DataFrame()
    proba = bundle["model"].predict_proba(feats[bundle["feature_columns"]])[:, 1]
    out = pd.DataFrame({"proba_up": proba}, index=feats.index)
    out["signal"] = (out["proba_up"] >= 0.5).astype(int)
    return out


def predict_from_processed_csv(processed_df: pd.DataFrame, symbol: str, freq: str = "5min") -> pd.DataFrame:
    """Pipeline complet à partir des sorties consumer pour un symbole."""
    if processed_df.empty:
        return pd.DataFrame()
    sub = processed_df[processed_df.get("symbol") == symbol] if "symbol" in processed_df.columns else processed_df
    bars = _ticks_to_bars(sub, freq=freq)
    if bars.empty or len(bars) < 30:
        return pd.DataFrame()
    return predict_from_history(bars)
