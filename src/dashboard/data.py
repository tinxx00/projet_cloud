"""Data access layer for the dashboard.

Cached CSV loaders + helpers used by the views. Keeping this isolated
makes views thin and easy to swap.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


RAW_DATA_PATH = Path("data/quotes_backup.csv")
PROCESSED_DATA_PATH = Path("data/processed_quotes.csv")


NUMERIC_COLS = [
    "price_current",
    "price_high",
    "price_low",
    "price_open",
    "price_previous_close",
    "delta_abs",
    "delta_pct",
    "volume",
]
DATE_COLS = ["ingested_at", "processed_at", "finnhub_timestamp"]


@dataclass(frozen=True)
class DatasetStatus:
    path: Path
    exists: bool
    rows: int
    last_update: datetime | None
    file_size_bytes: int


def _file_signature(path: Path) -> tuple[float, int]:
    """Return (mtime, size) so Streamlit cache invalidates when files change."""
    if not path.exists():
        return (0.0, 0)
    stat = path.stat()
    return (stat.st_mtime, stat.st_size)


@st.cache_data(show_spinner=False, ttl=2)
def _load_csv(path_str: str, signature: tuple[float, int]) -> pd.DataFrame:
    """Internal cached loader. ``signature`` makes the cache filesystem-aware."""
    path = Path(path_str)
    if not path.exists() or signature[1] == 0:
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty:
        return df
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in DATE_COLS:
        if col not in df.columns:
            continue
        # `finnhub_timestamp` est un epoch (secondes) côté Finnhub.
        # Les autres colonnes sont des ISO timestamps écrits par le pipeline.
        if col == "finnhub_timestamp" and pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce", utc=True)
        else:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    if "ingested_at" in df.columns:
        df = df.sort_values("ingested_at")
    return df.reset_index(drop=True)


def load_quotes(path: Path) -> pd.DataFrame:
    """Public loader, transparently cached against file mtime/size."""
    return _load_csv(str(path), _file_signature(path))


def dataset_status(path: Path) -> DatasetStatus:
    if not path.exists():
        return DatasetStatus(path=path, exists=False, rows=0, last_update=None, file_size_bytes=0)
    df = load_quotes(path)
    last_update = None
    if not df.empty and "ingested_at" in df.columns:
        ts = df["ingested_at"].dropna()
        if not ts.empty:
            last_update = ts.max().to_pydatetime()
    return DatasetStatus(
        path=path,
        exists=True,
        rows=int(len(df)),
        last_update=last_update,
        file_size_bytes=int(path.stat().st_size),
    )


def latest_per_symbol(df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest row per symbol, sorted by symbol."""
    if df.empty or "symbol" not in df.columns:
        return pd.DataFrame()
    sort_col = "ingested_at" if "ingested_at" in df.columns else None
    work = df.sort_values(sort_col) if sort_col else df
    out = work.groupby("symbol", as_index=False).tail(1).reset_index(drop=True)
    return out.sort_values("symbol").reset_index(drop=True)


def filter_symbols(df: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    if not symbols or "symbol" not in df.columns:
        return df
    return df[df["symbol"].isin(symbols)].copy()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
