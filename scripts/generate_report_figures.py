"""Génère les figures du rapport à partir des artefacts d'entraînement.

Produit des PNG dans reports/figures/ :
  - comparaison des modèles (AUC)
  - courbe ROC, précision-rappel, calibration, matrice de confusion
  - distribution des probabilités prédites
  - historique AutoML (Optuna)
  - courbes d'équity du backtest
  - courbe d'apprentissage (train vs validation) + importance des variables

Usage : PYTHONPATH=src python scripts/generate_report_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

MODELS_DIR = Path("data/models")
HISTORY_DIR = Path("data/history")
OUT = Path("reports/figures")
OUT.mkdir(parents=True, exist_ok=True)

VIOLET, PINK, GREEN, RED, GREY = "#8B5CF6", "#DB2777", "#059669", "#F43F5E", "#94A3B8"
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25})


def _save(fig, name: str):
    fig.tight_layout()
    path = OUT / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path}")


def fig_model_comparison():
    report = json.loads((MODELS_DIR / "training_report.json").read_text())
    summary, best = report["summary"], report.get("best_model")
    names = list(summary.keys())
    auc = [summary[n]["roc_auc_mean"] for n in names]
    std = [summary[n].get("roc_auc_std", 0) for n in names]
    order = np.argsort(auc)
    names = [names[i] for i in order]; auc = [auc[i] for i in order]; std = [std[i] for i in order]
    colors = [GREEN if n == best else VIOLET for n in names]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(names, auc, xerr=std, color=colors, alpha=0.9, capsize=3)
    ax.axvline(0.5, ls="--", color=RED, label="Aléatoire (0.5)")
    ax.set_xlim(0.48, max(auc) + max(std) + 0.01)
    ax.set_xlabel("ROC AUC (moyenne ± écart-type, walk-forward CV)")
    ax.set_title("Comparaison des modèles — AUC")
    ax.legend()
    _save(fig, "01_comparaison_modeles.png")


def _oof_best():
    df = pd.read_csv(MODELS_DIR / "oof_predictions.csv")
    report = json.loads((MODELS_DIR / "training_report.json").read_text())
    best = report.get("best_model", "xgb")
    sub = df[[best, "label"]].dropna()
    return sub["label"].astype(int).values, sub[best].astype(float).values, best


def fig_roc_pr_calibration():
    from sklearn.metrics import roc_curve, auc, precision_recall_curve
    from sklearn.calibration import calibration_curve
    y, p, best = _oof_best()

    fpr, tpr, _ = roc_curve(y, p)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color=VIOLET, lw=2, label=f"{best.upper()} (AUC={auc(fpr,tpr):.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color=GREY)
    ax.set_xlabel("Taux de faux positifs"); ax.set_ylabel("Taux de vrais positifs")
    ax.set_title("Courbe ROC (out-of-fold)"); ax.legend()
    _save(fig, "02_courbe_roc.png")

    prec, rec, _ = precision_recall_curve(y, p)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(rec, prec, color=PINK, lw=2)
    ax.axhline(y.mean(), ls="--", color=GREY, label=f"Base rate ({y.mean():.2f})")
    ax.set_xlabel("Rappel"); ax.set_ylabel("Précision")
    ax.set_title("Courbe Précision-Rappel"); ax.legend()
    _save(fig, "03_precision_rappel.png")

    frac_pos, mean_pred = calibration_curve(y, p, n_bins=10, strategy="quantile")
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(mean_pred, frac_pos, "o-", color=VIOLET, label=best.upper())
    ax.plot([0, 1], [0, 1], ls="--", color=GREY, label="Parfaitement calibré")
    ax.set_xlabel("Probabilité prédite moyenne"); ax.set_ylabel("Fréquence observée")
    ax.set_title("Courbe de calibration"); ax.legend()
    _save(fig, "04_calibration.png")


def fig_confusion_and_dist():
    from sklearn.metrics import confusion_matrix
    y, p, best = _oof_best()
    pred = (p >= 0.5).astype(int)
    cm = confusion_matrix(y, pred)
    fig, ax = plt.subplots(figsize=(5, 4.5))
    im = ax.imshow(cm, cmap="Purples")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=14)
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["Baisse", "Hausse"]); ax.set_yticklabels(["Baisse", "Hausse"])
    ax.set_xlabel("Prédit"); ax.set_ylabel("Réel")
    ax.set_title(f"Matrice de confusion — {best.upper()} (seuil 0.5)")
    fig.colorbar(im, fraction=0.046)
    _save(fig, "05_matrice_confusion.png")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(p[y == 1], bins=30, alpha=0.6, color=GREEN, label="Hausse réelle")
    ax.hist(p[y == 0], bins=30, alpha=0.6, color=RED, label="Baisse réelle")
    ax.axvline(0.5, ls="--", color=GREY)
    ax.set_xlabel("Probabilité de hausse prédite"); ax.set_ylabel("Nombre")
    ax.set_title(f"Distribution des probabilités prédites — {best.upper()}"); ax.legend()
    _save(fig, "06_distribution_probas.png")


def fig_automl():
    automl = json.loads((MODELS_DIR / "automl_report.json").read_text())
    top = automl.get("top10", [])
    if not top:
        return
    trials = [t["trial"] for t in top]
    aucs = [t["auc"] for t in top]
    order = np.argsort(trials)
    trials = [trials[i] for i in order]; aucs = [aucs[i] for i in order]
    best = max(aucs)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(trials, aucs, "o-", color=VIOLET)
    ax.axhline(best, ls="--", color=GREEN, label=f"Meilleur AUC ({best:.3f})")
    ax.set_xlabel("N° d'essai (trial Optuna)"); ax.set_ylabel("ROC AUC")
    ax.set_title(f"AutoML Optuna — meilleurs essais ({automl.get('n_trials','?')} au total)")
    ax.legend()
    _save(fig, "07_automl_optuna.png")


def fig_backtest():
    files = sorted(MODELS_DIR.glob("backtest_*.csv"))
    if not files:
        return
    n = len(files)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4), squeeze=False)
    for ax, f in zip(axes[0], files):
        sym = f.stem.replace("backtest_", "")
        df = pd.read_csv(f)
        x = range(len(df))
        ax.plot(x, df["equity_strat"], color=VIOLET, lw=1.8, label="Stratégie")
        ax.plot(x, df["equity_bh"], color=GREY, lw=1.5, ls="--", label="Buy & Hold")
        ax.set_title(sym); ax.set_xlabel("Jours (test)")
    axes[0][0].set_ylabel("Équity (base 1.0)")
    axes[0][0].legend()
    fig.suptitle("Backtest out-of-sample — Stratégie vs Buy & Hold", y=1.03)
    _save(fig, "08_backtest_equity.png")


def fig_learning_curve_and_importance():
    """Courbe d'apprentissage réelle (train vs validation) + importance des variables."""
    from ml.features import FEATURE_COLUMNS, build_features, make_label
    import xgboost as xgb

    symbols = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
    frames = []
    for sym in symbols:
        p = HISTORY_DIR / f"{sym}_1d.parquet"
        if not p.exists():
            continue
        hist = pd.read_parquet(p)
        feats = build_features(hist)
        y = make_label(hist, horizon=1, threshold_bps=5.0)
        d = feats.copy()
        d["label"] = y
        frames.append(d.dropna(subset=["label"]))
    if not frames:
        return
    data = pd.concat(frames).sort_index()
    data = data.dropna(subset=FEATURE_COLUMNS)
    X = data[FEATURE_COLUMNS].values
    y = data["label"].astype(int).values
    cut = int(len(X) * 0.8)
    Xtr, Xva, ytr, yva = X[:cut], X[cut:], y[:cut], y[cut:]

    model = xgb.XGBClassifier(
        n_estimators=300, max_depth=3, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, eval_metric="auc",
        early_stopping_rounds=None, use_label_encoder=False,
    )
    model.fit(Xtr, ytr, eval_set=[(Xtr, ytr), (Xva, yva)], verbose=False)
    res = model.evals_result()
    tr = res["validation_0"]["auc"]; va = res["validation_1"]["auc"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(tr, color=VIOLET, label="Entraînement")
    ax.plot(va, color=PINK, label="Validation")
    ax.axhline(0.5, ls="--", color=GREY)
    ax.set_xlabel("Nombre d'arbres (itérations de boosting)"); ax.set_ylabel("ROC AUC")
    ax.set_title("Courbe d'apprentissage — XGBoost (train vs validation)"); ax.legend()
    _save(fig, "09_courbe_apprentissage.png")

    imp = model.feature_importances_
    order = np.argsort(imp)[-15:]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.barh([FEATURE_COLUMNS[i] for i in order], imp[order], color=VIOLET, alpha=0.9)
    ax.set_xlabel("Importance"); ax.set_title("Importance des variables — XGBoost (top 15)")
    _save(fig, "10_importance_variables.png")


def main():
    print(f"Génération des figures dans {OUT}/ …")
    steps = [
        ("comparaison modèles", fig_model_comparison),
        ("ROC / PR / calibration", fig_roc_pr_calibration),
        ("confusion / distribution", fig_confusion_and_dist),
        ("AutoML", fig_automl),
        ("backtest", fig_backtest),
        ("courbe d'apprentissage + importances", fig_learning_curve_and_importance),
    ]
    for label, fn in steps:
        try:
            fn()
        except Exception as exc:
            print(f"  ⚠️ {label} ignoré : {exc}")
    print("Terminé.")


if __name__ == "__main__":
    main()
