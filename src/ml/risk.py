"""Risk metrics + placement recommendation logic.

Pour chaque symbole, on calcule des indicateurs de risque (volatilité
annualisée, drawdown max, Sharpe) à partir de l'historique long. Puis on
score les placements contre le profil de risque de l'utilisateur :

    score = α · match_risque + (1-α) · score_rendement

où ``match_risque = 1 - |risk_score_symbole - profil_utilisateur|``.

Le profil utilisateur ∈ [0, 1] :
    0 = très prudent, 0.5 = équilibré, 1 = audacieux.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.dataset import fetch_history, load_cached, save_cached


def _ensure_history(symbol: str, period: str = "3y", interval: str = "1d") -> pd.DataFrame:
    df = load_cached(symbol, interval)
    if df is not None and not df.empty:
        return df
    df = fetch_history(symbol, period=period, interval=interval)
    if not df.empty:
        save_cached(symbol, interval, df)
    return df


def _metrics_one(symbol: str, df: pd.DataFrame) -> dict | None:
    if df.empty or "Close" not in df.columns:
        return None
    rets = df["Close"].pct_change().dropna()
    if len(rets) < 30:
        return None
    vol = float(rets.std() * np.sqrt(252))
    mean_ret = float(rets.mean() * 252)
    cum = (1 + rets).cumprod()
    max_dd = float((cum / cum.cummax() - 1).min())
    sharpe = mean_ret / (vol + 1e-9)
    return {
        "symbol": symbol,
        "volatility_annual": vol,
        "expected_return_annual": mean_ret,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "n_obs": int(len(rets)),
    }


def compute_universe_metrics(symbols: list[str]) -> pd.DataFrame:
    """Calcule les métriques de risque pour chaque symbole.

    Renvoie un DataFrame normalisé avec ``risk_score`` et ``return_score``
    en rang relatif (0..1) au sein de l'univers — robuste aux outliers.
    """
    rows = []
    for sym in symbols:
        df = _ensure_history(sym)
        m = _metrics_one(sym, df)
        if m:
            rows.append(m)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["risk_score"] = out["volatility_annual"].rank(pct=True)
    out["return_score"] = out["expected_return_annual"].rank(pct=True)
    return out


def _risk_label(risk_score: float) -> str:
    if risk_score < 0.34:
        return "Faible"
    if risk_score < 0.67:
        return "Modéré"
    return "Élevé"


def recommend(metrics: pd.DataFrame, user_risk_pref: float, alpha: float = 0.6) -> pd.DataFrame:
    """Score chaque placement vs le profil utilisateur, trie par score décroissant."""
    if metrics.empty:
        return metrics
    df = metrics.copy()
    df["match_score"] = 1.0 - (df["risk_score"] - user_risk_pref).abs()
    df["score"] = alpha * df["match_score"] + (1 - alpha) * df["return_score"]
    df["risk_label"] = df["risk_score"].apply(_risk_label)
    return df.sort_values("score", ascending=False).reset_index(drop=True)


# --- Apprentissage du profil ----------------------------------------------------

LEARNING_RATE = 0.35
NUDGE = 0.15  # écart utilisé pour transformer une note en cible de profil


def feedback_to_target(risk_score: float, rating: str) -> float:
    """Convertit une note utilisateur sur un placement en valeur cible de profil.

    - "too_risky"        → l'utilisateur veut quelque chose de moins risqué que ce placement
    - "good"             → le placement matchait son profil
    - "not_enough_risk"  → l'utilisateur veut plus risqué
    """
    if rating == "too_risky":
        return max(0.0, risk_score - NUDGE)
    if rating == "not_enough_risk":
        return min(1.0, risk_score + NUDGE)
    return float(risk_score)  # "good"


def update_pref(current_pref: float, target: float, lr: float = LEARNING_RATE) -> float:
    """EMA classique : pref ← pref + lr · (cible - pref), clamp [0,1]."""
    new = current_pref + lr * (target - current_pref)
    return float(max(0.0, min(1.0, new)))


def replay_history(initial_pref: float, feedback_df: pd.DataFrame,
                   lr: float = LEARNING_RATE) -> list[tuple[pd.Timestamp, float]]:
    """Rejoue l'historique de feedbacks pour produire la trajectoire du profil."""
    if feedback_df.empty:
        return []
    trail = []
    pref = float(initial_pref)
    for _, row in feedback_df.sort_values("timestamp").iterrows():
        target = feedback_to_target(float(row["risk_score"]), str(row["user_rating"]))
        pref = update_pref(pref, target, lr=lr)
        trail.append((row["timestamp"], pref))
    return trail
