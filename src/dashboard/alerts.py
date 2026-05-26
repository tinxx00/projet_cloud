"""Alert engine — détection de pics et envoi d'emails.

Analyse les prédictions ML pour détecter les signaux forts (hausse/baisse)
et envoie un email à l'utilisateur abonné.
"""
from __future__ import annotations

import json
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd

ALERTS_LOG_PATH = Path("data/alerts_log.json")

# ─── SMTP config (Gmail App Password recommandé) ──────────────────────────────
# Mettre ces variables dans un fichier .env ou les passer en paramètre
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = ""   # ex: "votre.app@gmail.com"
SMTP_PASS = ""   # App Password Gmail


def _load_log() -> list:
    if not ALERTS_LOG_PATH.exists():
        return []
    try:
        return json.loads(ALERTS_LOG_PATH.read_text())
    except Exception:
        return []


def _save_log(log: list) -> None:
    ALERTS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALERTS_LOG_PATH.write_text(json.dumps(log[-500:], indent=2, ensure_ascii=False))


def _already_alerted(user_id: str, symbol: str, direction: str, window_minutes: int = 60) -> bool:
    """Évite le spam : max 1 alerte par heure par user/symbole/direction."""
    log = _load_log()
    now = datetime.now(timezone.utc)
    for entry in log:
        if (entry.get("user_id") == user_id
                and entry.get("symbol") == symbol
                and entry.get("direction") == direction):
            ts = datetime.fromisoformat(entry["timestamp"])
            diff = (now - ts).total_seconds() / 60
            if diff < window_minutes:
                return True
    return False


def _log_alert(user_id: str, symbol: str, direction: str, proba: float, email: str) -> None:
    log = _load_log()
    log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "symbol": symbol,
        "direction": direction,
        "proba": round(proba, 4),
        "email": email,
    })
    _save_log(log)


def send_alert_email(to_email: str, user_name: str, symbol: str,
                     direction: str, proba: float,
                     smtp_user: str = SMTP_USER,
                     smtp_pass: str = SMTP_PASS) -> bool:
    """Envoie un email d'alerte. Retourne True si succès."""
    if not smtp_user or not smtp_pass:
        return False

    emoji = "🚀" if direction == "UP" else "🔻"
    color = "#10B981" if direction == "UP" else "#EF4444"
    label = "HAUSSE" if direction == "UP" else "BAISSE"
    pct = f"{proba * 100:.1f}%"

    subject = f"{emoji} Alerte {label} — {symbol} | Market Platform"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0B1020;color:#E2E8F0;padding:2rem;">
    <div style="max-width:500px;margin:auto;background:#141A2E;border-radius:12px;padding:2rem;border:1px solid #27314D;">
      <h2 style="color:#22D3EE;margin-top:0;">💹 Market Platform</h2>
      <p>Bonjour <b>{user_name}</b>,</p>
      <div style="background:{color}22;border:1px solid {color};border-radius:8px;padding:1.2rem;margin:1.2rem 0;text-align:center;">
        <div style="font-size:2.5rem;">{emoji}</div>
        <div style="font-size:1.8rem;font-weight:800;color:{color};">{label} DÉTECTÉE</div>
        <div style="font-size:1.2rem;margin-top:0.5rem;"><b>{symbol}</b></div>
        <div style="color:#94A3B8;margin-top:0.3rem;">Probabilité : <b style="color:{color};">{pct}</b></div>
      </div>
      <p style="color:#94A3B8;font-size:0.85rem;">
        Signal généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M UTC')}.<br>
        <i>Ce signal est fourni à titre informatif et ne constitue pas un conseil en investissement.</i>
      </p>
      <p style="color:#475569;font-size:0.75rem;">Market Platform — Désactivez vos alertes dans votre profil.</p>
    </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[alerts] Email error: {e}")
        return False


def check_and_alert(user: dict, predictions: dict[str, pd.DataFrame],
                    smtp_user: str = SMTP_USER, smtp_pass: str = SMTP_PASS) -> list[dict]:
    """
    Vérifie les prédictions pour les symboles suivis par l'utilisateur.
    Envoie des alertes si seuils franchis.
    
    predictions: {symbol: DataFrame avec colonne 'proba_up'}
    Retourne la liste des alertes déclenchées.
    """
    alerts_cfg = user.get("alerts", {})
    if not alerts_cfg.get("enabled"):
        return []

    uid = user["id"]
    email = user["email"]
    name = user.get("name", "Utilisateur")
    symbols = alerts_cfg.get("symbols", [])
    thr_up = float(alerts_cfg.get("threshold_up", 0.70))
    thr_down = float(alerts_cfg.get("threshold_down", 0.30))

    triggered = []
    for sym in symbols:
        preds = predictions.get(sym)
        if preds is None or preds.empty or "proba_up" not in preds.columns:
            continue
        last_proba = float(preds["proba_up"].iloc[-1])

        # Hausse
        if last_proba >= thr_up and not _already_alerted(uid, sym, "UP"):
            sent = send_alert_email(email, name, sym, "UP", last_proba, smtp_user, smtp_pass)
            _log_alert(uid, sym, "UP", last_proba, email)
            triggered.append({"symbol": sym, "direction": "UP", "proba": last_proba, "sent": sent})

        # Baisse
        elif last_proba <= thr_down and not _already_alerted(uid, sym, "DOWN"):
            sent = send_alert_email(email, name, sym, "DOWN", last_proba, smtp_user, smtp_pass)
            _log_alert(uid, sym, "DOWN", last_proba, email)
            triggered.append({"symbol": sym, "direction": "DOWN", "proba": last_proba, "sent": sent})

    return triggered


def get_alerts_log(user_id: str | None = None, limit: int = 50) -> list[dict]:
    log = _load_log()
    if user_id:
        log = [e for e in log if e.get("user_id") == user_id]
    return log[-limit:]
