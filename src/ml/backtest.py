"""Backtest honnête (out-of-sample) du signal directionnel.

Stratégie:
1. On télécharge l'historique complet du symbole.
2. On coupe en TRAIN (les ``train_years`` premières années) et TEST (le reste).
3. On entraîne un modèle sur TRAIN uniquement (jamais le modèle de prod
   réentraîné sur tout l'historique → ce serait du leakage).
4. On score TEST, on simule la stratégie long/flat avec coûts, et on
   compare au buy-and-hold.

Lancer:
    PYTHONPATH=src python -m ml.backtest --symbols AAPL MSFT TSLA \\
        --period 10y --train-years 5 --threshold 0.55

Sortie:
    data/models/backtest_<symbol>.csv   (P&L barre par barre)
    data/models/backtest_summary.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from ml.dataset import fetch_history
from ml.features import FEATURE_COLUMNS, build_features, make_label
from ml.train import _build_models


MODEL_PATH = Path("data/models/direction_model.joblib")
OUT_DIR = Path("data/models")
SUMMARY_PATH = OUT_DIR / "backtest_summary.json"


def _max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    return float(dd.min())


def _sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    if returns.std() == 0 or len(returns) < 2:
        return 0.0
    return float(np.sqrt(periods_per_year) * returns.mean() / returns.std())


def _select_model_name() -> str:
    """Lit le rapport d'entraînement pour aligner le backtest sur le meilleur modèle."""
    report_path = OUT_DIR / "training_report.json"
    if report_path.exists():
        try:
            return json.loads(report_path.read_text()).get("best_model", "gbdt")
        except Exception:
            pass
    return "gbdt"


def backtest_symbol(
    symbol: str,
    period: str,
    interval: str,
    threshold: float,
    cost_bps: float,
    train_years: float = 5.0,
    horizon: int = 1,
    threshold_bps_label: float = 5.0,
) -> tuple[pd.DataFrame, dict]:
    """Out-of-sample backtest avec coupure temporelle stricte."""
    df = fetch_history(symbol, period=period, interval=interval)
    if df.empty:
        raise RuntimeError(f"No data for {symbol}")

    feats = build_features(df)
    label = make_label(df, horizon=horizon, threshold_bps=threshold_bps_label)
    aligned = pd.concat([feats, label.rename("label"), df["Close"]], axis=1).dropna()

    cutoff = aligned.index.min() + pd.DateOffset(years=int(train_years))
    train = aligned.loc[aligned.index < cutoff]
    test = aligned.loc[aligned.index >= cutoff]
    if len(train) < 200 or len(test) < 50:
        raise RuntimeError(
            f"Holdout insuffisant pour {symbol}: train={len(train)} test={len(test)}. "
            f"Augmente --period ou réduis --train-years."
        )

    model_name = _select_model_name()
    model = _build_models()[model_name]
    model.fit(train[FEATURE_COLUMNS], train["label"])

    proba = model.predict_proba(test[FEATURE_COLUMNS])[:, 1]
    out = test[["Close", "label"]].copy()
    out["proba_up"] = proba
    out["signal"] = (proba >= threshold).astype(int)

    out["fwd_ret"] = out["Close"].pct_change().shift(-1)
    pos_change = out["signal"].diff().abs().fillna(out["signal"])
    cost = pos_change * (cost_bps / 10_000.0)
    out["strategy_ret"] = out["signal"] * out["fwd_ret"] - cost
    out["bh_ret"] = out["fwd_ret"]

    out = out.dropna(subset=["strategy_ret", "bh_ret"])
    out["equity_strat"] = (1 + out["strategy_ret"]).cumprod()
    out["equity_bh"] = (1 + out["bh_ret"]).cumprod()

    n_trades = int((pos_change > 0).sum())
    n_long = int((out["signal"] == 1).sum())
    hit_rate = float(((out["signal"] == 1) & (out["fwd_ret"] > 0)).sum() / max(n_long, 1))

    summary = {
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "model": model_name,
        "threshold": threshold,
        "cost_bps": cost_bps,
        "train_years": train_years,
        "train_start": str(train.index.min().date()),
        "train_end": str(train.index.max().date()),
        "test_start": str(test.index.min().date()),
        "test_end": str(test.index.max().date()),
        "n_train": int(len(train)),
        "n_test": int(len(out)),
        "n_trades": n_trades,
        "exposure": float(out["signal"].mean()),
        "hit_rate": hit_rate,
        "total_return_strategy": float(out["equity_strat"].iloc[-1] - 1),
        "total_return_bh": float(out["equity_bh"].iloc[-1] - 1),
        "sharpe_strategy": _sharpe(out["strategy_ret"]),
        "sharpe_bh": _sharpe(out["bh_ret"]),
        "max_drawdown_strategy": _max_drawdown(out["equity_strat"]),
        "max_drawdown_bh": _max_drawdown(out["equity_bh"]),
    }
    return out, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "TSLA"])
    parser.add_argument("--period", default="10y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--train-years", type=float, default=5.0,
                        help="Nombre d'années réservées à l'entraînement (le reste devient le holdout test)")
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--cost-bps", type=float, default=2.0,
                        help="Coût aller-retour en bps appliqué à chaque changement de position")
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--threshold-bps-label", type=float, default=5.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for sym in args.symbols:
        sym = sym.upper()
        print(f"[info] backtest {sym}")
        try:
            bt, summary = backtest_symbol(
                sym, args.period, args.interval, args.threshold, args.cost_bps,
                train_years=args.train_years, horizon=args.horizon,
                threshold_bps_label=args.threshold_bps_label,
            )
        except Exception as exc:
            print(f"  [error] {exc}")
            continue
        out_csv = OUT_DIR / f"backtest_{sym}.csv"
        bt.to_csv(out_csv)
        summaries.append(summary)
        print(f"  test=[{summary['test_start']}..{summary['test_end']}] n={summary['n_test']} "
              f"strat={summary['total_return_strategy']:.2%} bh={summary['total_return_bh']:.2%} "
              f"sharpe={summary['sharpe_strategy']:.2f} hit={summary['hit_rate']:.2%} "
              f"trades={summary['n_trades']}")

    SUMMARY_PATH.write_text(json.dumps(summaries, indent=2))
    print(f"[ok] summary saved: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
