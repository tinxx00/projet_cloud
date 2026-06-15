"""AutoML avec Optuna — recherche automatique du meilleur modèle + hyperparamètres.

Optuna explore intelligemment l'espace des hyperparamètres (TPE sampler) 
et sélectionne automatiquement le meilleur modèle via walk-forward CV.

Lancer:
    PYTHONPATH=src python -m ml.automl --trials 50 --symbols AAPL MSFT TSLA GOOGL AMZN

Sortie:
    data/models/direction_model.joblib  (meilleur modèle trouvé)
    data/models/automl_report.json      (résultats de toutes les trials)
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import optuna
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from ml.dataset import fetch_history, load_cached, save_cached
from ml.features import FEATURE_COLUMNS, build_features, make_label

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

MODEL_DIR  = Path("data/models")
MODEL_PATH = MODEL_DIR / "direction_model.joblib"
REPORT_PATH = MODEL_DIR / "automl_report.json"


# ── Construction du modèle selon le type choisi par Optuna ────────────────────

def _make_pipeline(trial: optuna.Trial) -> Pipeline:
    model_type = trial.suggest_categorical("model", [
        "logreg", "gbdt", "rf", "et", "xgb", "lgbm", "mlp",
    ])

    if model_type == "logreg":
        C = trial.suggest_float("C", 0.01, 10.0, log=True)
        clf = LogisticRegression(C=C, max_iter=500, class_weight="balanced")

    elif model_type == "gbdt":
        clf = GradientBoostingClassifier(
            n_estimators=trial.suggest_int("n_est", 50, 300),
            max_depth=trial.suggest_int("depth", 2, 6),
            learning_rate=trial.suggest_float("lr", 0.01, 0.2, log=True),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            random_state=42,
        )

    elif model_type == "rf":
        clf = RandomForestClassifier(
            n_estimators=trial.suggest_int("n_est", 50, 300),
            max_depth=trial.suggest_int("depth", 3, 10),
            min_samples_leaf=trial.suggest_int("min_leaf", 5, 30),
            class_weight="balanced", random_state=42, n_jobs=-1,
        )

    elif model_type == "et":
        clf = ExtraTreesClassifier(
            n_estimators=trial.suggest_int("n_est", 50, 300),
            max_depth=trial.suggest_int("depth", 3, 10),
            min_samples_leaf=trial.suggest_int("min_leaf", 5, 30),
            class_weight="balanced", random_state=42, n_jobs=-1,
        )

    elif model_type == "xgb":
        clf = XGBClassifier(
            n_estimators=trial.suggest_int("n_est", 50, 300),
            max_depth=trial.suggest_int("depth", 2, 6),
            learning_rate=trial.suggest_float("lr", 0.01, 0.2, log=True),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample", 0.5, 1.0),
            eval_metric="logloss", random_state=42, verbosity=0,
        )

    elif model_type == "lgbm":
        clf = LGBMClassifier(
            n_estimators=trial.suggest_int("n_est", 50, 300),
            max_depth=trial.suggest_int("depth", 2, 6),
            learning_rate=trial.suggest_float("lr", 0.01, 0.2, log=True),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample", 0.5, 1.0),
            class_weight="balanced", random_state=42, verbosity=-1,
        )

    elif model_type == "mlp":
        n_layers = trial.suggest_int("n_layers", 1, 3)
        layer_size = trial.suggest_categorical("layer_size", [32, 64, 128, 256])
        hidden = tuple([layer_size] * n_layers)
        clf = MLPClassifier(
            hidden_layer_sizes=hidden,
            learning_rate_init=trial.suggest_float("lr", 1e-4, 1e-2, log=True),
            max_iter=300, early_stopping=True, random_state=42,
        )

    return Pipeline([("scaler", StandardScaler()), ("clf", clf)])


# ── Objectif Optuna ───────────────────────────────────────────────────────────

def _objective(trial: optuna.Trial, X: pd.DataFrame, y: pd.Series, n_splits: int) -> float:
    pipeline = _make_pipeline(trial)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    aucs = []
    for train_idx, test_idx in tscv.split(X):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        try:
            pipeline.fit(X_tr, y_tr)
            proba = pipeline.predict_proba(X_te)[:, 1]
            if len(set(y_te)) > 1:
                aucs.append(roc_auc_score(y_te, proba))
        except Exception:
            return 0.0
    return float(np.mean(aucs)) if aucs else 0.0


# ── Chargement données ────────────────────────────────────────────────────────

def _build_dataset(symbols: list[str], period: str, interval: str,
                   horizon: int, threshold_bps: float) -> pd.DataFrame:
    frames = []
    for sym in symbols:
        df = load_cached(sym, interval)
        if df is None or df.empty:
            df = fetch_history(sym, period=period, interval=interval)
            if df.empty:
                print(f"[warn] pas de données pour {sym}")
                continue
            save_cached(sym, interval, df)
        feats = build_features(df)
        label = make_label(df, horizon=horizon, threshold_bps=threshold_bps)
        merged = feats.copy()
        merged["label"] = label
        merged["symbol"] = sym
        frames.append(merged.dropna())
    return pd.concat(frames).sort_index()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"])
    parser.add_argument("--trials", type=int, default=50, help="Nombre de trials Optuna")
    parser.add_argument("--period", default="5y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--threshold-bps", type=float, default=5.0)
    parser.add_argument("--n-splits", type=int, default=5)
    args = parser.parse_args()

    print(f"[automl] Chargement des données…")
    df = _build_dataset(
        [s.upper() for s in args.symbols],
        args.period, args.interval, args.horizon, args.threshold_bps,
    )
    print(f"[automl] Dataset: {len(df):,} lignes | base rate: {df['label'].mean():.3f}")

    X = df[FEATURE_COLUMNS]
    y = df["label"].astype(int)

    print(f"[automl] Lancement Optuna — {args.trials} trials…")
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=10),
    )
    study.optimize(
        lambda trial: _objective(trial, X, y, args.n_splits),
        n_trials=args.trials,
        show_progress_bar=True,
    )

    best = study.best_trial
    print(f"\n[automl] ✅ Meilleur trial #{best.number}")
    print(f"  Modèle : {best.params.get('model', '?')}")
    print(f"  AUC    : {best.value:.4f}")
    print(f"  Params : {best.params}")

    # Réentraîner le meilleur sur tout le dataset
    print("\n[automl] Réentraînement final sur tout l'historique…")
    best_pipeline = _make_pipeline(best)
    best_pipeline.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": best_pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "best_name": f"automl_{best.params.get('model', 'unknown')}",
        "config": vars(args),
    }, MODEL_PATH)

    # Rapport complet
    trials_data = [
        {
            "trial": t.number,
            "auc": t.value,
            "params": t.params,
        }
        for t in study.trials if t.value is not None
    ]
    trials_data.sort(key=lambda x: x["auc"], reverse=True)

    REPORT_PATH.write_text(json.dumps({
        "best_model": best.params.get("model"),
        "best_auc": best.value,
        "best_params": best.params,
        "n_trials": len(study.trials),
        "top10": trials_data[:10],
    }, indent=2))

    print(f"[automl] Modèle sauvegardé → {MODEL_PATH}")
    print(f"[automl] Rapport sauvegardé → {REPORT_PATH}")

    # Résumé top 5
    print("\n[automl] Top 5 trials :")
    for t in trials_data[:5]:
        print(f"  #{t['trial']:3d} | {t['params'].get('model', '?'):8s} | AUC={t['auc']:.4f} | {t['params']}")


if __name__ == "__main__":
    main()
