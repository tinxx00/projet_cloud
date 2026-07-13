"""Worker autonome — vérifie les pics de prix toutes les N minutes
et envoie des alertes email automatiquement, sans que personne soit connecté.

Lancé comme service systemd indépendant du dashboard.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve()
_SRC  = _HERE.parent
_ROOT = _HERE.parents[1]
for _p in (_SRC, _ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd
from dashboard import alerts as alerts_module
from ml import predict as ml_predict

USERS_PATH      = _ROOT / "data" / "users.json"
PROCESSED_PATH  = _ROOT / "data" / "processed_quotes.csv"
RAW_PATH        = _ROOT / "data" / "quotes_backup.csv"
HISTORY_DIR     = _ROOT / "data" / "history"
CHECK_EVERY     = 120   # secondes entre chaque vérification


def _ml_predictions(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Probabilités de hausse par symbole, calculées sur l'historique quotidien."""
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        path = HISTORY_DIR / f"{sym}_1d.parquet"
        if not path.exists():
            continue
        try:
            res = ml_predict.predict_from_history(pd.read_parquet(path))
            if not res.empty:
                out[sym] = res
        except Exception:
            continue
    return out

# ── helpers ───────────────────────────────────────────────────────────────────

def _load_users() -> list[dict]:
    if not USERS_PATH.exists():
        return []
    try:
        data = json.loads(USERS_PATH.read_text())
        return list(data.values()) if isinstance(data, dict) else data
    except Exception:
        return []


def _load_df() -> pd.DataFrame:
    for path in [PROCESSED_PATH, RAW_PATH]:
        if path.exists() and path.stat().st_size > 0:
            try:
                return pd.read_csv(path)
            except Exception:
                continue
    return pd.DataFrame()


def run_once() -> None:
    """Un cycle de vérification pour tous les utilisateurs avec alertes activées."""
    users = _load_users()
    active = [u for u in users if u.get("alerts", {}).get("enabled")]

    if not active:
        print("[worker] Aucun utilisateur avec alertes activées.")
        return

    df = _load_df()  # peut être vide (mode démo sans pipeline live)

    for user in active:
        symbols = user.get("alerts", {}).get("symbols", [])

        # 1) Signaux ML (historique quotidien — toujours disponible)
        preds = _ml_predictions(symbols)
        triggered = alerts_module.check_and_alert(user, preds)

        # 2) Pics de prix live (si des données consumer existent)
        if not df.empty:
            triggered += alerts_module.check_price_spikes(user, df)

        for a in triggered:
            emoji = "🚀" if a["direction"] == "UP" else "🔻"
            sent  = "📧 email envoyé" if a.get("sent") else "pas de SMTP"
            detail = f"{a.get('pct', a.get('proba', 0)):+.2f}"
            print(f"[worker] {emoji} {user['email']} | {a['symbol']} {a['direction']} "
                  f"{detail} → {sent}")
        if not triggered:
            print(f"[worker] {user['email']} : aucun seuil franchi ({len(symbols)} symboles suivis).")


def main() -> None:
    print(f"[worker] Démarrage — vérification toutes les {CHECK_EVERY}s")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[worker] Erreur: {e}")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
