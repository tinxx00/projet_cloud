"""Entraîne un classifieur de direction court-terme avec walk-forward CV.

Lancer:
    PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN \\
        --period 5y --interval 1d --horizon 1 --threshold-bps 5

Sortie:
    data/models/direction_model.joblib
    data/models/training_report.json
    data/models/oof_predictions.csv
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import joblib

from ml.dataset import fetch_history, load_cached, save_cached
from ml.features import FEATURE_COLUMNS, build_features, make_label


MODEL_DIR = Path("data/models")
MODEL_PATH = MODEL_DIR / "direction_model.joblib"
REPORT_PATH = MODEL_DIR / "training_report.json"
OOF_PATH = MODEL_DIR / "oof_predictions.csv"


@dataclass
class TrainConfig:
    symbols: list[str]
    period: str
    interval: str
    horizon: int
    threshold_bps: float
    n_splits: int
    use_cache: bool


def _build_dataset(cfg: TrainConfig) -> pd.DataFrame:
    """Concatène features + label de plusieurs symboles."""
    frames = []
    for sym in cfg.symbols:
        df = load_cached(sym, cfg.interval) if cfg.use_cache else None
        if df is None or df.empty:
            df = fetch_history(sym, period=cfg.period, interval=cfg.interval)
            if df.empty:
                print(f"[warn] no data for {sym}, skipping")
                continue
            save_cached(sym, cfg.interval, df)
        feats = build_features(df)
        label = make_label(df, horizon=cfg.horizon, threshold_bps=cfg.threshold_bps)
        merged = feats.copy()
        merged["label"] = label
        merged["symbol"] = sym
        merged = merged.dropna()
        frames.append(merged)
    if not frames:
        raise RuntimeError("No data available for any symbol")
    full = pd.concat(frames).sort_index()
    return full


def _build_models() -> dict[str, Pipeline]:
    return {
        "logreg": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500, class_weight="balanced", C=0.5)),
        ]),
        "gbdt": Pipeline([
            ("scaler", StandardScaler(with_mean=False)),
            ("clf", GradientBoostingClassifier(
                n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.85, random_state=42,
            )),
        ]),
    }


def _score_fold(y_true: np.ndarray, proba: np.ndarray) -> dict[str, float]:
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, proba)) if len(set(y_true)) > 1 else float("nan"),
        "log_loss": float(log_loss(y_true, np.clip(proba, 1e-6, 1 - 1e-6))),
    }


def walk_forward(X: pd.DataFrame, y: pd.Series, n_splits: int) -> tuple[pd.DataFrame, dict[str, list[dict]]]:
    """Walk-forward time-series CV: chaque fold s'entraîne sur le passé seul."""
    splitter = TimeSeriesSplit(n_splits=n_splits)
    models = _build_models()

    oof = pd.DataFrame(index=X.index)
    for name in models:
        oof[name] = np.nan

    fold_scores: dict[str, list[dict]] = {name: [] for name in models}

    for fold_id, (train_idx, test_idx) in enumerate(splitter.split(X)):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        for name, model in models.items():
            model.fit(X_tr, y_tr)
            proba = model.predict_proba(X_te)[:, 1]
            oof.iloc[test_idx, oof.columns.get_loc(name)] = proba
            scores = _score_fold(y_te.values, proba)
            scores["fold"] = fold_id
            fold_scores[name].append(scores)
            print(f"  fold {fold_id} | {name:>7} | acc={scores['accuracy']:.3f} auc={scores['roc_auc']:.3f} f1={scores['f1']:.3f}")

    return oof, fold_scores


def aggregate(fold_scores: dict[str, list[dict]]) -> dict[str, dict[str, float]]:
    summary = {}
    for name, folds in fold_scores.items():
        df = pd.DataFrame(folds).drop(columns=["fold"])
        summary[name] = {f"{c}_mean": float(df[c].mean()) for c in df.columns}
        summary[name].update({f"{c}_std": float(df[c].std()) for c in df.columns})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"])
    parser.add_argument("--period", default="5y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--threshold-bps", type=float, default=5.0,
                        help="Seuil en points de base pour considérer un mouvement directionnel (anti-bruit)")
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    cfg = TrainConfig(
        symbols=[s.upper() for s in args.symbols],
        period=args.period,
        interval=args.interval,
        horizon=args.horizon,
        threshold_bps=args.threshold_bps,
        n_splits=args.n_splits,
        use_cache=not args.no_cache,
    )

    print(f"[info] config: {asdict(cfg)}")
    df = _build_dataset(cfg)
    print(f"[info] dataset: {len(df):,} rows | base rate (label=1): {df['label'].mean():.3f}")

    X = df[FEATURE_COLUMNS]
    y = df["label"].astype(int)

    print("[info] walk-forward CV")
    oof, fold_scores = walk_forward(X, y, n_splits=cfg.n_splits)
    summary = aggregate(fold_scores)

    print("[info] CV summary:")
    for name, stats in summary.items():
        print(f"  {name}: acc={stats['accuracy_mean']:.3f}±{stats['accuracy_std']:.3f} "
              f"auc={stats['roc_auc_mean']:.3f}±{stats['roc_auc_std']:.3f} "
              f"f1={stats['f1_mean']:.3f}±{stats['f1_std']:.3f}")

    # Choisit le meilleur modèle par AUC moyenne, tie-break F1
    best_name = max(summary.keys(), key=lambda n: (summary[n]["roc_auc_mean"], summary[n]["f1_mean"]))
    print(f"[info] best model: {best_name}")

    # Réentraîne le meilleur sur tout l'historique pour la production
    final_model = _build_models()[best_name]
    final_model.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": final_model,
        "feature_columns": FEATURE_COLUMNS,
        "best_name": best_name,
        "config": asdict(cfg),
    }, MODEL_PATH)

    REPORT_PATH.write_text(json.dumps({
        "config": asdict(cfg),
        "summary": summary,
        "best_model": best_name,
        "n_rows": int(len(df)),
        "base_rate": float(y.mean()),
    }, indent=2))

    oof_out = oof.copy()
    oof_out["label"] = y
    oof_out["symbol"] = df["symbol"]
    oof_out.to_csv(OOF_PATH)

    print(f"[ok] model saved: {MODEL_PATH}")
    print(f"[ok] report saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
