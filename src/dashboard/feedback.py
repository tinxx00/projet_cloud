"""User feedback storage for placement recommendations.

Stocke les notations utilisateur dans ``data/user_feedback.csv`` en
mode append — ce CSV constitue le dataset de personnalisation qui
permet d'adapter le moteur de recommandation au profil de chaque user.
"""
from __future__ import annotations

import csv
import uuid
from pathlib import Path

import pandas as pd


FEEDBACK_PATH = Path("data/user_feedback.csv")

FIELDS = [
    "timestamp",
    "user_id",
    "symbol",
    "risk_score",
    "risk_label",
    "user_rating",
    "user_pref_before",
    "user_pref_after",
    "score",
]

VALID_RATINGS = {"too_risky", "good", "not_enough_risk"}


def get_or_create_user_id(session_state) -> str:
    """Persist a per-session user id into Streamlit ``session_state``."""
    if "user_id" not in session_state:
        session_state["user_id"] = uuid.uuid4().hex[:8]
    return session_state["user_id"]


def append_feedback(record: dict) -> None:
    if record.get("user_rating") not in VALID_RATINGS:
        raise ValueError(f"invalid rating: {record.get('user_rating')!r}")
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = FEEDBACK_PATH.exists() and FEEDBACK_PATH.stat().st_size > 0
    with FEEDBACK_PATH.open("a", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: record.get(k) for k in FIELDS})


def load_feedback(user_id: str | None = None) -> pd.DataFrame:
    if not FEEDBACK_PATH.exists():
        return pd.DataFrame(columns=FIELDS)
    df = pd.read_csv(FEEDBACK_PATH)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    if user_id:
        df = df[df["user_id"] == user_id]
    return df.reset_index(drop=True)


def reset_user_feedback(user_id: str) -> int:
    """Drop all feedback rows for ``user_id``. Returns number of rows removed."""
    if not FEEDBACK_PATH.exists():
        return 0
    df = pd.read_csv(FEEDBACK_PATH)
    if df.empty:
        return 0
    n = int((df["user_id"] == user_id).sum())
    df = df[df["user_id"] != user_id]
    df.to_csv(FEEDBACK_PATH, index=False)
    return n
