"""Technical indicator features for short-term direction prediction.

Conçu pour être appliqué sur des barres OHLC (historiques yfinance ou
agrégations du flux Finnhub). Toutes les features sont calculées en
fenêtre glissante et alignées strictement sur le passé pour éviter
toute fuite de données.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLUMNS: list[str] = [
    "ret_1",
    "ret_3",
    "ret_5",
    "ret_10",
    "vol_5",
    "vol_10",
    "ema_fast_gap",
    "ema_slow_gap",
    "ema_cross",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_pct",
    "atr_pct",
    "high_low_range",
    "close_to_high",
    "close_to_low",
    "volume_z",
    "momentum_10",
]


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build a feature DataFrame indexed like ``df``.

    Expected columns: Open, High, Low, Close, Volume.
    """
    out = pd.DataFrame(index=df.index)
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    volume = df["Volume"].astype(float) if "Volume" in df.columns else pd.Series(0.0, index=df.index)

    log_ret = np.log(close / close.shift(1))
    out["ret_1"] = log_ret
    out["ret_3"] = log_ret.rolling(3).sum()
    out["ret_5"] = log_ret.rolling(5).sum()
    out["ret_10"] = log_ret.rolling(10).sum()

    out["vol_5"] = log_ret.rolling(5).std()
    out["vol_10"] = log_ret.rolling(10).std()

    ema_fast = _ema(close, 12)
    ema_slow = _ema(close, 26)
    out["ema_fast_gap"] = (close - ema_fast) / close
    out["ema_slow_gap"] = (close - ema_slow) / close
    out["ema_cross"] = (ema_fast - ema_slow) / close

    out["rsi_14"] = _rsi(close, 14)

    macd_line = ema_fast - ema_slow
    macd_signal = _ema(macd_line, 9)
    out["macd"] = macd_line / close
    out["macd_signal"] = macd_signal / close
    out["macd_hist"] = (macd_line - macd_signal) / close

    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    width = (upper - lower).replace(0, np.nan)
    out["bb_pct"] = (close - lower) / width

    atr = _atr(df, 14)
    out["atr_pct"] = atr / close

    out["high_low_range"] = (high - low) / close
    out["close_to_high"] = (high.rolling(10).max() - close) / close
    out["close_to_low"] = (close - low.rolling(10).min()) / close

    vol_mean = volume.rolling(20).mean()
    vol_std = volume.rolling(20).std().replace(0, np.nan)
    out["volume_z"] = ((volume - vol_mean) / vol_std).fillna(0.0)

    out["momentum_10"] = (close / close.shift(10)) - 1

    return out[FEATURE_COLUMNS]


def make_label(df: pd.DataFrame, horizon: int = 1, threshold_bps: float = 0.0) -> pd.Series:
    """Build a binary label: 1 if next ``horizon`` close return > ``threshold_bps`` (basis points).

    Threshold permet d'ignorer les micro-mouvements (bruit) et d'apprendre
    seulement sur les vraies impulsions directionnelles.
    """
    close = df["Close"].astype(float)
    fwd_ret = close.shift(-horizon) / close - 1
    threshold = threshold_bps / 10_000.0
    return (fwd_ret > threshold).astype(int)
