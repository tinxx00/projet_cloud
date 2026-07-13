"""Alert engine — détection de pics et envoi d'emails.

Analyse les prédictions ML pour détecter les signaux forts (hausse/baisse)
et envoie un email à l'utilisateur abonné.
"""
from __future__ import annotations

import json
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd

ALERTS_LOG_PATH = Path("data/alerts_log.json")

# ─── Chargement .env ──────────────────────────────────────────────────────────
def _load_env() -> None:
    _here = Path(__file__).resolve()
    candidates = [
        Path.home() / "PA" / ".env",   # EC2 ~/PA/.env
        _here.parents[3] / ".env",      # repo root
        _here.parents[2] / ".env",      # src/
        Path(".env"),                    # cwd
    ]
    for p in candidates:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            break

_load_env()

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
_ANTISPAM_MINUTES = int(os.environ.get("ALERT_ANTISPAM_MINUTES", "5"))


def smtp_configured() -> bool:
    """True si les identifiants SMTP sont présents."""
    return bool(SMTP_USER and SMTP_PASS)


def _deliver(to_email: str, msg, smtp_user: str, smtp_pass: str) -> None:
    """Envoie un message via SSL (465) ou STARTTLS (587/autre)."""
    ctx = ssl.create_default_context()
    sender = SMTP_FROM or smtp_user
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender, to_email, msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=ctx)
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender, to_email, msg.as_string())


def send_alerts_enabled_email(to_email: str, user_name: str, symbols: list[str],
                              thr_up: float, thr_down: float) -> bool:
    """Email de confirmation envoyé automatiquement quand l'utilisateur active ses alertes."""
    if not smtp_configured():
        return False
    syms = ", ".join(symbols) if symbols else "aucun (ajoutez-en dans votre profil)"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🔔 Vos alertes MarketPilot sont activées"
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to_email
    html = f"""
    <html><body style="font-family:Arial,sans-serif;padding:2rem;color:#3B3560;">
      <div style="max-width:500px;margin:auto;border:1px solid #E6DCF7;border-radius:14px;padding:1.8rem;">
        <h2 style="color:#8B5CF6;margin-top:0;">💹 MarketPilot</h2>
        <p>Bonjour <b>{user_name}</b>,</p>
        <p>🔔 Vos <b>alertes email sont activées</b>. Vous serez prévenu automatiquement
        dès qu'un signal fort est détecté par notre IA — sans avoir à ouvrir l'application.</p>
        <div style="background:rgba(139,92,246,0.08);border:1px solid #E6DCF7;border-radius:10px;padding:1rem;margin:1rem 0;">
          <div style="font-size:0.9rem;"><b>Actifs surveillés :</b> {syms}</div>
          <div style="font-size:0.9rem;margin-top:0.4rem;"><b>Seuils :</b>
            hausse ≥ {thr_up:.0%} · baisse ≤ {thr_down:.0%}</div>
        </div>
        <p style="color:#8983A6;font-size:0.8rem;">
          Vous pouvez modifier ou désactiver vos alertes à tout moment dans « Mon compte ».<br>
          <i>Les signaux sont fournis à titre informatif et ne constituent pas un conseil en investissement.</i>
        </p>
      </div>
    </body></html>
    """
    msg.attach(MIMEText(html, "html"))
    try:
        _deliver(to_email, msg, SMTP_USER, SMTP_PASS)
        return True
    except Exception as e:
        print(f"[alerts] Confirmation email error: {e}")
        return False


def send_test_email(to_email: str, user_name: str = "Utilisateur") -> tuple[bool, str]:
    """Envoie un email de test pour vérifier la configuration SMTP."""
    if not smtp_configured():
        return False, "SMTP non configuré (SMTP_USER / SMTP_PASS manquants dans .env)."
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "✅ Test d'alerte — MarketPilot"
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to_email
    html = f"""
    <html><body style="font-family:Arial,sans-serif;padding:2rem;color:#3B3560;">
      <div style="max-width:480px;margin:auto;border:1px solid #E6DCF7;border-radius:14px;padding:1.8rem;">
        <h2 style="color:#8B5CF6;margin-top:0;">💹 MarketPilot</h2>
        <p>Bonjour <b>{user_name}</b>,</p>
        <p>✅ Votre configuration d'alertes email fonctionne correctement.<br>
        Vous recevrez désormais un email dès qu'un signal fort est détecté sur vos actions.</p>
        <p style="color:#8983A6;font-size:0.8rem;">Ceci est un message de test — aucune action requise.</p>
      </div>
    </body></html>
    """
    msg.attach(MIMEText(html, "html"))
    try:
        _deliver(to_email, msg, SMTP_USER, SMTP_PASS)
        return True, f"Email de test envoyé à {to_email}."
    except Exception as e:
        return False, f"Échec de l'envoi : {e}"



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


def _already_alerted(user_id: str, symbol: str, direction: str, window_minutes: int | None = None) -> bool:
    """Évite le spam : max 1 alerte par _ANTISPAM_MINUTES par user/symbole/direction."""
    if window_minutes is None:
        window_minutes = _ANTISPAM_MINUTES
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
    <html><body style="font-family:Arial,sans-serif;background:#0C0A1F;color:#E2E8F0;padding:2rem;">
    <div style="max-width:500px;margin:auto;background:#17132E;border-radius:12px;padding:2rem;border:1px solid #322A5C;">
      <h2 style="color:#A855F7;margin-top:0;">💹 Market Platform</h2>
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
        _deliver(to_email, msg, smtp_user, smtp_pass)
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


def check_price_spikes(
    user: dict,
    processed_df: "pd.DataFrame",
    spike_pct: float = 0.05,
    window: int = 10,
    smtp_user: str = SMTP_USER,
    smtp_pass: str = SMTP_PASS,
) -> list[dict]:
    """
    Détecte des pics de prix réels (sans ML) sur le CSV processed.

    Un pic est détecté si le prix a varié de ±spike_pct % sur les `window`
    dernières lignes pour un symbole. Anti-spam 60 min inclus.

    Retourne la liste des alertes déclenchées (pour affichage toast).
    """
    alerts_cfg = user.get("alerts", {})
    if not alerts_cfg.get("enabled"):
        return []
    if processed_df is None or processed_df.empty:
        return []

    uid = user["id"]
    email = user["email"]
    name = user.get("name", "Utilisateur")
    symbols = alerts_cfg.get("symbols", [])
    thr_up = float(alerts_cfg.get("spike_pct_up", spike_pct))
    thr_down = float(alerts_cfg.get("spike_pct_down", spike_pct))

    triggered = []
    price_col = "price_current" if "price_current" in processed_df.columns else "price"
    sym_col = "symbol" if "symbol" in processed_df.columns else None

    for sym in symbols:
        if sym_col:
            sub = processed_df[processed_df[sym_col] == sym]
        else:
            sub = processed_df
        if sub.empty or price_col not in sub.columns:
            continue

        prices = sub[price_col].dropna().astype(float)
        if len(prices) < 2:
            continue

        recent = prices.iloc[-min(window, len(prices)):]
        pct_change = (recent.iloc[-1] - recent.iloc[0]) / (recent.iloc[0] + 1e-9) * 100

        if pct_change >= thr_up and not _already_alerted(uid, sym, "UP"):
            sent = send_alert_email(email, name, sym, "UP", min(pct_change / 100, 1.0),
                                    smtp_user, smtp_pass)
            _log_alert(uid, sym, "UP", pct_change / 100, email)
            triggered.append({
                "symbol": sym, "direction": "UP",
                "pct": round(pct_change, 2), "sent": sent,
            })

        elif pct_change <= -thr_down and not _already_alerted(uid, sym, "DOWN"):
            sent = send_alert_email(email, name, sym, "DOWN", abs(pct_change) / 100,
                                    smtp_user, smtp_pass)
            _log_alert(uid, sym, "DOWN", abs(pct_change) / 100, email)
            triggered.append({
                "symbol": sym, "direction": "DOWN",
                "pct": round(pct_change, 2), "sent": sent,
            })

    return triggered


def get_alerts_log(user_id: str | None = None, limit: int = 50) -> list[dict]:
    log = _load_log()
    if user_id:
        log = [e for e in log if e.get("user_id") == user_id]
    return list(reversed(log))[:limit]
