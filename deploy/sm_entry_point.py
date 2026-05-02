"""SageMaker SKLearn entry point — entraîne le modèle de direction court-terme.

Ce script est exécuté par SageMaker dans le conteneur SKLearn.
Il lit les données depuis /opt/ml/input/data/training/ et sauvegarde
le modèle dans /opt/ml/model/.

Variables d'environnement SageMaker injectées automatiquement :
  SM_MODEL_DIR           → /opt/ml/model
  SM_CHANNEL_TRAINING    → /opt/ml/input/data/training
  SM_OUTPUT_DATA_DIR     → /opt/ml/output/data
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, log_loss, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ── Chemins SageMaker ────────────────────────────────────────────────────────
MODEL_DIR = Path(os.environ.get("SM_MODEL_DIR", "data/models"))
DATA_DIR  = Path(os.environ.get("SM_CHANNEL_TRAINING", "data"))
OUTPUT_DIR = Path(os.environ.get("SM_OUTPUT_DATA_DIR", "data/models"))

# ── Features ─────────────────────────────────────────────────────────────────
FEATURE_COLUMNS: list[str] = [
    "ret_1", "ret_3", "ret_5", "ret_10",
    "vol_5", "vol_10",
    "ema_fast_gap", "ema_slow_gap", "ema_cross",
    "rsi_14",
    "macd", "macd_signal", "macd_hist",
    "bb_pct", "atr_pct",
    "high_low_range", "close_to_high", "close_to_low",
    "volume_z", "momentum_10",
]


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    close  = df["Close"].astype(float)
    high   = df["High"].astype(float)
    low    = df["Low"].astype(float)
    volume = df["Volume"].astype(float) if "Volume" in df.columns else pd.Series(0.0, index=df.index)

    log_ret = np.log(close / close.shift(1))
    out["ret_1"]  = log_ret
    out["ret_3"]  = log_ret.rolling(3).sum()
    out["ret_5"]  = log_ret.rolling(5).sum()
    out["ret_10"] = log_ret.rolling(10).sum()
    out["vol_5"]  = log_ret.rolling(5).std()
    out["vol_10"] = log_ret.rolling(10).std()

    ema_fast = _ema(close, 12)
    ema_slow = _ema(close, 26)
    out["ema_fast_gap"] = (close - ema_fast) / close
    out["ema_slow_gap"] = (close - ema_slow) / close
    out["ema_cross"]    = (ema_fast - ema_slow) / close
    out["rsi_14"]       = _rsi(close, 14)

    macd_line   = ema_fast - ema_slow
    macd_signal = _ema(macd_line, 9)
    out["macd"]        = macd_line / close
    out["macd_signal"] = macd_signal / close
    out["macd_hist"]   = (macd_line - macd_signal) / close

    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    out["bb_pct"] = (close - lower) / (upper - lower).replace(0, np.nan)

    out["atr_pct"]       = _atr(df, 14) / close
    out["high_low_range"] = (high - low) / close
    out["close_to_high"]  = (high.rolling(10).max() - close) / close
    out["close_to_low"]   = (close - low.rolling(10).min()) / close

    vol_mean = volume.rolling(20).mean()
    vol_std  = volume.rolling(20).std().replace(0, np.nan)
    out["volume_z"]    = ((volume - vol_mean) / vol_std).fillna(0.0)
    out["momentum_10"] = (close / close.shift(10)) - 1

    return out[FEATURE_COLUMNS]


def make_label(df: pd.DataFrame, horizon: int = 1, threshold_bps: float = 5.0) -> pd.Series:
    close   = df["Close"].astype(float)
    fwd_ret = close.shift(-horizon) / close - 1
    return (fwd_ret > threshold_bps / 10_000.0).astype(int)


def _build_models() -> dict[str, Pipeline]:
    return {
        "logreg": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500, class_weight="balanced", C=0.5)),
        ]),
        "gbdt": Pipeline([
            ("scaler", StandardScaler(with_mean=False)),
            ("clf", GradientBoostingClassifier(
                n_estimators=200, max_depth=3, learning_rate=0.05,
                subsample=0.85, random_state=42,
            )),
        ]),
    }


def _score(y_true, proba) -> dict:
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy":  float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall":    float(recall_score(y_true, pred, zero_division=0)),
        "f1":        float(f1_score(y_true, pred, zero_division=0)),
        "roc_auc":   float(roc_auc_score(y_true, proba)) if len(set(y_true)) > 1 else float("nan"),
        "log_loss":  float(log_loss(y_true, np.clip(proba, 1e-6, 1 - 1e-6))),
    }


def walk_forward(X, y, n_splits=5):
    splitter = TimeSeriesSplit(n_splits=n_splits)
    models   = _build_models()
    oof      = pd.DataFrame(index=X.index)
    for name in models:
        oof[name] = np.nan
    fold_scores = {name: [] for name in models}

    for fold_id, (tr_idx, te_idx) in enumerate(splitter.split(X)):
        X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
        y_tr, y_te = y.iloc[tr_idx], y.iloc[te_idx]
        for name, m in models.items():
            m.fit(X_tr, y_tr)
            proba = m.predict_proba(X_te)[:, 1]
            oof.iloc[te_idx, oof.columns.get_loc(name)] = proba
            sc = _score(y_te.values, proba)
            sc["fold"] = fold_id
            fold_scores[name].append(sc)
            print(f"  fold {fold_id} | {name:>7} | acc={sc['accuracy']:.3f} auc={sc['roc_auc']:.3f} f1={sc['f1']:.3f}")

    return oof, fold_scores


def aggregate(fold_scores):
    summary = {}
    for name, folds in fold_scores.items():
        df = pd.DataFrame(folds).drop(columns=["fold"])
        summary[name] = {f"{c}_mean": float(df[c].mean()) for c in df.columns}
        summary[name].update({f"{c}_std": float(df[c].std()) for c in df.columns})
    return summary


def load_history(symbols: list[str], period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    """Télécharge les données OHLCV via yfinance directement dans le container SageMaker.
    
    Pas besoin de canal S3 — yfinance télécharge depuis internet.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("yfinance non installé — ajouter dans requirements.txt du container")

    frames = []
    for sym in symbols:
        print(f"  Téléchargement {sym}...")
        df = yf.download(sym, period=period, interval=interval, auto_adjust=True, progress=False)
        if df.empty:
            print(f"[warn] Pas de données pour {sym}, ignoré")
            continue
        # Aplatir MultiIndex si nécessaire
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        feats = build_features(df)
        label = make_label(df)
        merged = feats.copy()
        merged["label"]  = label
        merged["symbol"] = sym
        frames.append(merged.dropna())
    if not frames:
        raise RuntimeError("Aucune donnée disponible pour les symboles demandés")
    return pd.concat(frames).sort_index()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols",       nargs="+", default=["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"])
    parser.add_argument("--horizon",       type=int,   default=1)
    parser.add_argument("--threshold-bps", type=float, default=5.0)
    parser.add_argument("--n-splits",      type=int,   default=5)
    args = parser.parse_args()

    symbols = [s.upper() for s in args.symbols]
    print(f"[info] Symboles : {symbols}")
    print(f"[info] DATA_DIR : {DATA_DIR}")
    print(f"[info] MODEL_DIR: {MODEL_DIR}")

    print(f"[info] Téléchargement des données via yfinance...")
    df = load_history(symbols)
    print(f"[info] Dataset : {len(df):,} lignes | base rate={df['label'].mean():.3f}")

    X = df[FEATURE_COLUMNS]
    y = df["label"].astype(int)

    print("[info] Walk-forward CV...")
    oof, fold_scores = walk_forward(X, y, n_splits=args.n_splits)
    summary = aggregate(fold_scores)

    best_name = max(summary.keys(), key=lambda n: (summary[n]["roc_auc_mean"], summary[n]["f1_mean"]))
    print(f"[info] Meilleur modèle : {best_name}")

    # Ré-entraîne sur tout le dataset
    final_model = _build_models()[best_name]
    final_model.fit(X, y)

    # Sauvegarde le modèle
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_bundle = {
        "model": final_model,
        "feature_columns": FEATURE_COLUMNS,
        "best_name": best_name,
        "config": {
            "symbols": symbols,
            "horizon": args.horizon,
            "threshold_bps": args.threshold_bps,
            "n_splits": args.n_splits,
        },
    }
    joblib.dump(model_bundle, MODEL_DIR / "direction_model.joblib")

    # Rapport d'entraînement
    report = {
        "config":     model_bundle["config"],
        "summary":    summary,
        "best_model": best_name,
        "n_rows":     int(len(df)),
        "base_rate":  float(y.mean()),
    }
    (MODEL_DIR / "training_report.json").write_text(json.dumps(report, indent=2))

    # OOF predictions
    oof["label"]  = y
    oof["symbol"] = df["symbol"]
    oof.to_csv(MODEL_DIR / "oof_predictions.csv")

    # Copie aussi dans output pour récupération facile
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "training_report.json").write_text(json.dumps(report, indent=2))

    print(f"[ok] Modèle sauvegardé dans {MODEL_DIR}/direction_model.joblib")


if __name__ == "__main__":
    main()
