"""Chargement de l'historique OHLC pour l'entraînement et le backtest."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class HistoricalConfig:
    symbols: tuple[str, ...]
    period: str = "5y"
    interval: str = "1d"


def fetch_history(symbol: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    """Télécharge l'historique OHLCV via yfinance.

    Renvoie un DataFrame indexé par date avec colonnes ``Open, High, Low, Close, Volume``.
    """
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=False)
    if df.empty:
        return df
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def fetch_many(symbols: list[str], period: str = "5y", interval: str = "1d") -> dict[str, pd.DataFrame]:
    return {sym: fetch_history(sym, period=period, interval=interval) for sym in symbols}


def cache_path(symbol: str, interval: str) -> Path:
    return Path("data") / "history" / f"{symbol}_{interval}.parquet"


def load_cached(symbol: str, interval: str) -> pd.DataFrame | None:
    path = cache_path(symbol, interval)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def save_cached(symbol: str, interval: str, df: pd.DataFrame) -> None:
    path = cache_path(symbol, interval)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
