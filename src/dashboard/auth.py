"""Authentication module — login/signup with email.

Stocke les utilisateurs dans ``data/users.json``.
Gère la session Streamlit et les préférences d'alertes.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

USERS_PATH = Path("data/users.json")

_PBKDF2_ROUNDS = 200_000


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    """Hash salé PBKDF2-HMAC-SHA256. Format: ``pbkdf2$<rounds>$<salt_hex>$<hash_hex>``."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2${_PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def _verify(password: str, stored: str) -> bool:
    """Vérifie un mot de passe. Supporte l'ancien format SHA-256 nu (legacy)."""
    if stored.startswith("pbkdf2$"):
        try:
            _, rounds, salt_hex, hash_hex = stored.split("$", 3)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
            )
            return hmac.compare_digest(dk.hex(), hash_hex)
        except (ValueError, TypeError):
            return False
    # Legacy: SHA-256 sans sel (anciens comptes)
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)


def _load_users() -> dict:
    if not USERS_PATH.exists():
        return {}
    try:
        return json.loads(USERS_PATH.read_text())
    except Exception:
        return {}


def _save_users(users: dict) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USERS_PATH.write_text(json.dumps(users, indent=2, ensure_ascii=False))


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email.strip()))


# ─── Public API ───────────────────────────────────────────────────────────────

def is_logged_in() -> bool:
    return st.session_state.get("auth_user") is not None


def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def current_user_id() -> str:
    u = current_user()
    return u["id"] if u else "anonymous"


def current_user_email() -> str:
    u = current_user()
    return u.get("email", "") if u else ""


def logout() -> None:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


def signup(name: str, email: str, password: str) -> tuple[bool, str]:
    email = email.strip().lower()
    if not name.strip():
        return False, "Le nom est requis."
    if not _valid_email(email):
        return False, "Email invalide."
    if len(password) < 6:
        return False, "Mot de passe trop court (min 6 caractères)."
    users = _load_users()
    if any(u["email"] == email for u in users.values()):
        return False, "Cet email est déjà utilisé."
    uid = uuid.uuid4().hex[:12]
    users[uid] = {
        "id": uid,
        "name": name.strip(),
        "email": email,
        "password_hash": _hash(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "alerts": {"enabled": False, "symbols": [], "threshold_up": 0.70, "threshold_down": 0.30},
        "risk_pref": 0.5,
    }
    _save_users(users)
    return True, uid


def login(email: str, password: str) -> tuple[bool, str]:
    email = email.strip().lower()
    users = _load_users()
    for uid, u in users.items():
        if u["email"] == email and _verify(password, u.get("password_hash", "")):
            # Migration transparente des anciens hashs SHA-256 vers PBKDF2
            if not u.get("password_hash", "").startswith("pbkdf2$"):
                u["password_hash"] = _hash(password)
                users[uid] = u
                _save_users(users)
            st.session_state["auth_user"] = u
            st.session_state["user_id"] = uid
            return True, ""
    return False, "Email ou mot de passe incorrect."


DEMO_EMAIL = "demo@marketpilot.io"
DEMO_PASSWORD = "demo1234"


def ensure_demo_user() -> None:
    """Crée le compte de démonstration s'il n'existe pas déjà."""
    users = _load_users()
    if any(u.get("email") == DEMO_EMAIL for u in users.values()):
        return
    uid = "demo00000000"
    users[uid] = {
        "id": uid,
        "name": "Invité Démo",
        "email": DEMO_EMAIL,
        "password_hash": _hash(DEMO_PASSWORD),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "alerts": {"enabled": True, "symbols": ["AAPL", "TSLA"], "threshold_up": 0.65, "threshold_down": 0.35},
        "risk_pref": 0.5,
    }
    _save_users(users)


def demo_login() -> None:
    """Connecte directement l'utilisateur au compte de démonstration."""
    ensure_demo_user()
    login(DEMO_EMAIL, DEMO_PASSWORD)


def get_user(uid: str) -> dict | None:
    return _load_users().get(uid)


def update_user(uid: str, updates: dict) -> None:
    users = _load_users()
    if uid in users:
        users[uid].update(updates)
        _save_users(users)
        # refresh session
        if st.session_state.get("auth_user", {}).get("id") == uid:
            st.session_state["auth_user"] = users[uid]


def update_alerts(uid: str, alerts_cfg: dict | None = None,
                  enabled: bool | None = None, symbols: list[str] | None = None,
                  threshold_up: float | None = None, threshold_down: float | None = None) -> None:
    """Met à jour la config alertes. Accepte soit un dict complet, soit des kwargs."""
    if alerts_cfg is not None:
        update_user(uid, {"alerts": alerts_cfg})
    else:
        cfg: dict = {}
        if enabled is not None:
            cfg["enabled"] = enabled
        if symbols is not None:
            cfg["symbols"] = symbols
        if threshold_up is not None:
            cfg["threshold_up"] = threshold_up
        if threshold_down is not None:
            cfg["threshold_down"] = threshold_down
        update_user(uid, {"alerts": cfg})


def update_risk_pref(uid: str, pref: float) -> None:
    update_user(uid, {"risk_pref": pref})


# ─── Login/Signup UI ──────────────────────────────────────────────────────────

_AUTH_CSS = """
<style>
section[data-testid="stSidebar"] { display: none !important; }
.block-container { max-width: 1160px !important; padding-top: 1.4rem !important; position: relative; z-index: 1; }

/* Arrière-plan animé de signaux */
.signal-bg-wrap { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
.signal-bg-wrap svg { width: 100%; height: 100%; display: block; }

/* Barre du haut */
.lp-logo-row { display: flex; align-items: center; gap: 0.7rem; padding-top: 0.2rem; }
.lp-mark { width: 46px; height: 46px; border-radius: 13px; flex-shrink: 0;
    background: linear-gradient(135deg, #8B5CF6, #DB2777); display: flex; align-items: center; justify-content: center;
    box-shadow: 0 8px 20px rgba(139,92,246,0.35); }
.lp-name { font-weight: 900; font-size: 1.35rem; letter-spacing: -0.02em; line-height: 1;
    background: linear-gradient(135deg, #7C3AED, #DB2777);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.lp-tag { font-size: 0.68rem; color: var(--text-muted); letter-spacing: 0.14em; text-transform: uppercase; margin-top: 2px; }

/* Hero */
.lp-hero { text-align: center; margin: 2.4rem auto 0.6rem; max-width: 52rem; }
.lp-badge { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; font-weight: 700;
    color: var(--primary); background: rgba(139,92,246,0.12); border: 1px solid rgba(139,92,246,0.3);
    padding: 0.3rem 0.85rem; border-radius: 999px; margin-bottom: 1.1rem; }
.lp-title { font-size: 3.1rem; font-weight: 900; letter-spacing: -0.035em; line-height: 1.05; margin: 0 0 1rem;
    background: linear-gradient(135deg, #7C3AED 0%, #A855F7 45%, #DB2777 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.lp-lead { color: var(--text-muted); font-size: 1.12rem; line-height: 1.6; max-width: 40rem; margin: 0 auto; }

/* Grille de features */
.lp-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 2.2rem 0 1rem; }
.lp-card { background: linear-gradient(150deg, var(--surface), var(--surface-alt)); border: 1px solid var(--border);
    border-radius: 18px; padding: 1.3rem 1.4rem; box-shadow: 0 6px 20px rgba(139,92,246,0.06);
    transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease; }
.lp-card:hover { transform: translateY(-4px); border-color: rgba(139,92,246,0.5); box-shadow: 0 16px 36px rgba(139,92,246,0.16); }
.lp-card-ic { width: 46px; height: 46px; border-radius: 13px; display: flex; align-items: center; justify-content: center;
    font-size: 1.45rem; margin-bottom: 0.7rem; }
.lp-card-t { font-weight: 800; font-size: 1.05rem; color: var(--text); margin-bottom: 0.25rem; }
.lp-card-d { font-size: 0.88rem; color: var(--text-muted); line-height: 1.5; }

/* Bandeau chiffres */
.lp-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2rem 0;
    background: linear-gradient(150deg, var(--surface), var(--surface-alt)); border: 1px solid var(--border);
    border-radius: 18px; padding: 1.4rem 1.2rem; }
.lp-stat { text-align: center; }
.lp-stat-n { font-size: 1.9rem; font-weight: 900; letter-spacing: -0.02em;
    background: linear-gradient(135deg, #8B5CF6, #DB2777);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.lp-stat-l { font-size: 0.76rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.2rem; }

/* Étapes */
.lp-steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1.4rem 0 2rem; }
.lp-step { padding: 1.2rem 1.3rem; border: 1px dashed var(--border); border-radius: 16px; }
.lp-step-n { width: 32px; height: 32px; border-radius: 10px; background: rgba(139,92,246,0.12); color: var(--primary);
    font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 0.6rem; }
.lp-step-t { font-weight: 800; color: var(--text); margin-bottom: 0.2rem; }
.lp-step-d { font-size: 0.86rem; color: var(--text-muted); line-height: 1.5; }

.lp-section-title { text-align: center; font-size: 1.5rem; font-weight: 800; color: var(--text); margin: 1.6rem 0 0.3rem; }
.lp-section-sub { text-align: center; color: var(--text-muted); font-size: 0.95rem; margin-bottom: 1rem; }
.lp-foot { text-align: center; color: var(--text-muted); font-size: 0.8rem; margin: 2rem 0 1rem;
    padding-top: 1.2rem; border-top: 1px solid var(--border); }

/* Carte graphique boursier (mock) */
.lp-chart-card { background: linear-gradient(150deg, var(--surface), var(--surface-alt)); border: 1px solid var(--border);
    border-radius: 20px; padding: 1.1rem 1.3rem; box-shadow: 0 14px 40px rgba(139,92,246,0.12);
    margin: 1.6rem auto 0; max-width: 780px; }
.lp-chart-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.lp-chart-sym { font-weight: 800; color: var(--text); font-size: 1.02rem; display: flex; align-items: center; gap: 0.5rem; }
.lp-chart-live { font-size: 0.68rem; font-weight: 700; color: var(--up); background: rgba(5,150,105,0.12);
    border: 1px solid rgba(5,150,105,0.3); border-radius: 999px; padding: 0.12rem 0.55rem; letter-spacing: 0.05em; }
.lp-chart-price { font-weight: 800; color: var(--up); font-size: 1.05rem; }
.lp-chart-card svg { width: 100%; height: 190px; display: block; }

/* Schéma flux de données */
.lp-flow { display: flex; align-items: stretch; justify-content: center; flex-wrap: wrap; gap: 0.2rem; margin: 1.2rem 0 2rem; }
.lp-flow-node { flex: 1 1 148px; max-width: 190px; text-align: center; padding: 1.1rem 0.8rem;
    background: linear-gradient(150deg, var(--surface), var(--surface-alt)); border: 1px solid var(--border);
    border-radius: 16px; box-shadow: 0 6px 20px rgba(139,92,246,0.06);
    transition: transform 160ms ease, border-color 160ms ease; }
.lp-flow-node:hover { transform: translateY(-3px); border-color: rgba(139,92,246,0.5); }
.lp-flow-ic { width: 48px; height: 48px; border-radius: 14px; margin: 0 auto 0.55rem; display: flex;
    align-items: center; justify-content: center; font-size: 1.5rem; background: rgba(139,92,246,0.12); }
.lp-flow-t { font-weight: 800; font-size: 0.92rem; color: var(--text); }
.lp-flow-d { font-size: 0.74rem; color: var(--text-muted); margin-top: 0.15rem; }
.lp-flow-arrow { display: flex; align-items: center; justify-content: center; color: var(--primary);
    font-size: 1.4rem; opacity: 0.75; min-width: 24px; }

/* Essai gratuit + tarifs */
.lp-trial { text-align: center; color: var(--text-muted); font-size: 0.86rem; margin: 0.6rem 0 0; }
.lp-pricing { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1.4rem 0 1rem; align-items: stretch; }
.lp-plan { background: linear-gradient(160deg, var(--surface), var(--surface-alt)); border: 1px solid var(--border);
    border-radius: 18px; padding: 1.6rem 1.4rem; display: flex; flex-direction: column;
    box-shadow: 0 6px 20px rgba(139,92,246,0.06); transition: transform 160ms ease, box-shadow 160ms ease; }
.lp-plan:hover { transform: translateY(-4px); box-shadow: 0 16px 36px rgba(139,92,246,0.16); }
.lp-plan.pop { border: 2px solid var(--primary); box-shadow: 0 16px 40px rgba(139,92,246,0.20); position: relative; }
.lp-plan-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
    background: linear-gradient(135deg, #8B5CF6, #DB2777); color: #fff; font-size: 0.68rem; font-weight: 800;
    padding: 0.25rem 0.85rem; border-radius: 999px; letter-spacing: 0.05em; white-space: nowrap; }
.lp-plan-name { font-size: 1.05rem; font-weight: 800; color: var(--text); }
.lp-plan-price { font-size: 2rem; font-weight: 900; color: var(--text); letter-spacing: -0.02em; margin: 0.4rem 0 0.1rem; }
.lp-plan-price small { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); }
.lp-plan-sub { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem; }
.lp-plan-feats { list-style: none; padding: 0; margin: 0 0 1.2rem; display: flex; flex-direction: column; gap: 0.5rem; }
.lp-plan-feats li { font-size: 0.86rem; color: var(--text); display: flex; gap: 0.5rem; align-items: flex-start; }
.lp-plan-feats li::before { content: '✓'; color: var(--up); font-weight: 800; }
.lp-plan-cta { margin-top: auto; text-align: center; font-weight: 700; font-size: 0.9rem; padding: 0.65rem;
    border-radius: 10px; background: rgba(139,92,246,0.1); color: var(--primary); border: 1px solid rgba(139,92,246,0.3); }
.lp-plan.pop .lp-plan-cta { background: linear-gradient(135deg, #7C3AED, #A855F7); color: #fff; border: none; }

@media (max-width: 900px) {
    .lp-grid, .lp-stats, .lp-steps, .lp-pricing { grid-template-columns: 1fr; }
    .lp-title { font-size: 2.2rem; }
    .lp-flow { flex-direction: column; align-items: center; }
    .lp-flow-node { max-width: 320px; width: 100%; }
    .lp-flow-arrow { transform: rotate(90deg); }
}
</style>
"""


def _signal_bg() -> str:
    """Arrière-plan corporate : grille de données très subtile + halos dégradés discrets."""
    return """
    <div class="signal-bg-wrap">
    <svg viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="160"/></filter>
        <pattern id="grid" width="46" height="46" patternUnits="userSpaceOnUse">
          <path d="M46 0H0V46" fill="none" stroke="#7C3AED" stroke-opacity="0.045" stroke-width="1"/>
        </pattern>
      </defs>

      <!-- fine grille de données -->
      <rect width="1440" height="900" fill="url(#grid)"/>

      <!-- halos dégradés discrets dans les coins -->
      <g filter="url(#soft)" opacity="0.30">
        <circle cx="130" cy="40" r="320" fill="#C4B5FD"/>
        <circle cx="1360" cy="880" r="320" fill="#F5C2E7"/>
      </g>

      <!-- fine ligne d'accent horizontale -->
      <line x1="0" y1="240" x2="1440" y2="240" stroke="#8B5CF6" stroke-opacity="0.05" stroke-width="1"/>
    </svg>
    </div>
    """


_LP_MARK = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M3 15.5L8.5 10l4 3.5L21 5" stroke="white" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M15 5h6v6" stroke="white" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


def _mock_chart_svg() -> str:
    """Graphique en chandeliers déterministe (données boursières fictives)."""
    import math

    W, H = 700, 190
    n = 24
    pad_l, pad_r, pad_t, pad_b = 14, 14, 16, 16
    closes: list[float] = []
    p = 42.0
    for i in range(n):
        p += math.sin(i * 0.6) * 5.5 + math.sin(i * 0.23) * 3.0 + 2.1
        closes.append(p)
    opens = [closes[0] - 2.0] + closes[:-1]
    highs = [max(o, c) + 2.4 + (i % 3) for i, (o, c) in enumerate(zip(opens, closes))]
    lows  = [min(o, c) - 2.4 - (i % 2) for i, (o, c) in enumerate(zip(opens, closes))]
    lo, hi = min(lows), max(highs)

    def y(v: float) -> float:
        return H - pad_b - (v - lo) / (hi - lo) * (H - pad_t - pad_b)

    step = (W - pad_l - pad_r) / n
    cw = step * 0.55
    parts: list[str] = []
    for i in range(n):
        cx = pad_l + step * (i + 0.5)
        o, c, h, l = opens[i], closes[i], highs[i], lows[i]
        col = "#059669" if c >= o else "#F43F5E"
        top = min(y(o), y(c))
        bh = max(abs(y(o) - y(c)), 2.0)
        parts.append(f'<line x1="{cx:.1f}" y1="{y(h):.1f}" x2="{cx:.1f}" y2="{y(l):.1f}" stroke="{col}" stroke-width="1.6" stroke-opacity="0.9"/>')
        parts.append(f'<rect x="{cx-cw/2:.1f}" y="{top:.1f}" width="{cw:.1f}" height="{bh:.1f}" rx="1.5" fill="{col}" fill-opacity="0.85"/>')

    pts = [(pad_l + step * (i + 0.5), y(closes[i])) for i in range(n)]
    line = "M" + " L".join(f"{x:.1f},{yv:.1f}" for x, yv in pts)
    area = line + f" L{pts[-1][0]:.1f},{H-pad_b} L{pts[0][0]:.1f},{H-pad_b} Z"
    candles = "".join(parts)
    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">'
        '<defs><linearGradient id="mcar" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#8B5CF6" stop-opacity="0.18"/>'
        '<stop offset="1" stop-color="#8B5CF6" stop-opacity="0"/></linearGradient></defs>'
        f'<path d="{area}" fill="url(#mcar)"/>'
        f'<path d="{line}" fill="none" stroke="#8B5CF6" stroke-opacity="0.55" stroke-width="1.6"/>'
        f'{candles}</svg>'
    )


@st.dialog("🔑 Connexion")
def _login_dialog() -> None:
    st.caption("Ravi de vous revoir 👋")
    email = st.text_input("Email", placeholder="vous@exemple.com", key="dlg_login_email")
    password = st.text_input("Mot de passe", type="password", key="dlg_login_pw")
    if st.button("Se connecter", type="primary", use_container_width=True, key="dlg_login_btn"):
        ok, msg = login(email, password)
        if ok:
            st.rerun()
        else:
            st.error(msg)


@st.dialog("✨ Créer un compte")
def _signup_dialog() -> None:
    st.caption("Quelques secondes suffisent.")
    name = st.text_input("Nom complet", placeholder="Marie Dupont", key="dlg_su_name")
    email = st.text_input("Email", placeholder="vous@exemple.com", key="dlg_su_email")
    pw = st.text_input("Mot de passe", type="password", key="dlg_su_pw")
    pw2 = st.text_input("Confirmer le mot de passe", type="password", key="dlg_su_pw2")
    if st.button("Créer mon compte", type="primary", use_container_width=True, key="dlg_su_btn"):
        if pw != pw2:
            st.error("Les mots de passe ne correspondent pas.")
        else:
            ok, result = signup(name, email, pw)
            if ok:
                login(email, pw)
                st.rerun()
            else:
                st.error(result)


def render_login_page() -> None:
    """Landing page complète avec Connexion / Inscription (modales)."""
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    st.markdown(_signal_bg(), unsafe_allow_html=True)

    # ── Barre du haut : logo à gauche, boutons à droite ────────────────────
    c_logo, _sp, c_login, c_signup = st.columns([4.4, 2.4, 1.25, 1.35], vertical_alignment="center")
    with c_logo:
        st.markdown(
            f'<div class="lp-logo-row"><div class="lp-mark">{_LP_MARK}</div>'
            f'<div><div class="lp-name">MarketPilot</div>'
            f'<div class="lp-tag">Invest smarter</div></div></div>',
            unsafe_allow_html=True,
        )
    with c_login:
        if st.button("Connexion", use_container_width=True, key="nav_login"):
            _login_dialog()
    with c_signup:
        if st.button("Inscription", use_container_width=True, type="primary", key="nav_signup"):
            _signup_dialog()

    # ── Hero ───────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="lp-hero">
          <div class="lp-badge">⚡ Analyse temps réel · Signaux par IA</div>
          <div class="lp-title">La donnée marché,<br>transformée en décisions.</div>
          <div class="lp-lead">
            Captez les mouvements en temps réel, laissez l'IA repérer les opportunités
            et recevez des alertes au bon moment — le tout dans une interface pensée
            pour décider vite et bien.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── CTA central (un seul bouton principal ; la connexion est en haut) ──
    _a, cta_primary, _b = st.columns([2.6, 1.8, 2.6])
    with cta_primary:
        if st.button("🚀 Créer un compte gratuit", use_container_width=True, type="primary", key="hero_signup"):
            _signup_dialog()

    st.markdown(
        '<div class="lp-trial">✓ Essai gratuit 30 jours · sans carte bancaire · sans engagement</div>',
        unsafe_allow_html=True,
    )

    # ── Features ───────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="lp-section-title">Tout ce dont vous avez besoin pour investir sereinement</div>
        <div class="lp-section-sub">Une plateforme complète, de la donnée brute à la décision.</div>
        <div class="lp-grid">
          <div class="lp-card"><div class="lp-card-ic" style="background:rgba(139,92,246,0.13);">📡</div>
            <div class="lp-card-t">Flux temps réel</div>
            <div class="lp-card-d">Cotations en continu via un pipeline Kafka scalable et résilient.</div></div>
          <div class="lp-card"><div class="lp-card-ic" style="background:rgba(219,39,119,0.13);">🤖</div>
            <div class="lp-card-t">Signaux par IA</div>
            <div class="lp-card-d">Des modèles entraînés et backtestés estiment la tendance court terme.</div></div>
          <div class="lp-card"><div class="lp-card-ic" style="background:rgba(245,63,94,0.13);">🔔</div>
            <div class="lp-card-t">Alertes intelligentes</div>
            <div class="lp-card-d">Notifié par email dès qu'une opportunité correspond à votre profil.</div></div>
          <div class="lp-card"><div class="lp-card-ic" style="background:rgba(99,102,241,0.13);">🎯</div>
            <div class="lp-card-t">Recommandations</div>
            <div class="lp-card-d">Des suggestions personnalisées selon votre tolérance au risque.</div></div>
          <div class="lp-card"><div class="lp-card-ic" style="background:rgba(5,150,105,0.13);">💬</div>
            <div class="lp-card-t">Coach IA</div>
            <div class="lp-card-d">Un assistant conversationnel pour interpréter les signaux et agir.</div></div>
          <div class="lp-card"><div class="lp-card-ic" style="background:rgba(217,119,6,0.13);">📈</div>
            <div class="lp-card-t">Tableau de bord</div>
            <div class="lp-card-d">Tendances, opportunités et portefeuille en un seul coup d'œil.</div></div>
        </div>

        <div class="lp-stats">
          <div class="lp-stat"><div class="lp-stat-n">Temps réel</div><div class="lp-stat-l">Flux marché</div></div>
          <div class="lp-stat"><div class="lp-stat-n">10+</div><div class="lp-stat-l">Actifs suivis</div></div>
          <div class="lp-stat"><div class="lp-stat-n">9</div><div class="lp-stat-l">Modèles comparés</div></div>
          <div class="lp-stat"><div class="lp-stat-n">24/7</div><div class="lp-stat-l">Coach IA</div></div>
        </div>

        <div class="lp-section-title">Comment ça marche</div>
        <div class="lp-section-sub">Trois étapes, aucune compétence technique requise.</div>
        <div class="lp-steps">
          <div class="lp-step"><div class="lp-step-n">1</div>
            <div class="lp-step-t">Créez votre compte</div>
            <div class="lp-step-d">Inscription en quelques secondes, puis définissez votre profil de risque.</div></div>
          <div class="lp-step"><div class="lp-step-n">2</div>
            <div class="lp-step-t">L'IA analyse le marché</div>
            <div class="lp-step-d">Les signaux et opportunités sont calculés et mis à jour en continu.</div></div>
          <div class="lp-step"><div class="lp-step-n">3</div>
            <div class="lp-step-t">Décidez & agissez</div>
            <div class="lp-step-d">Recevez des alertes claires et des recommandations adaptées à vos objectifs.</div></div>
        </div>

        <div class="lp-section-title">Un essai gratuit, puis des offres simples</div>
        <div class="lp-section-sub">Testez 30 jours gratuitement. Sans engagement, annulable à tout moment.</div>
        <div class="lp-pricing">
          <div class="lp-plan">
            <div class="lp-plan-name">Découverte</div>
            <div class="lp-plan-price">0€ <small>/ 30 jours</small></div>
            <div class="lp-plan-sub">Pour tester la plateforme</div>
            <ul class="lp-plan-feats">
              <li>Tableau de bord temps réel</li>
              <li>Signaux IA sur 3 actifs</li>
              <li>1 alerte email</li>
            </ul>
            <div class="lp-plan-cta">Commencer l'essai gratuit</div>
          </div>
          <div class="lp-plan pop">
            <div class="lp-plan-badge">LE PLUS POPULAIRE</div>
            <div class="lp-plan-name">Pro</div>
            <div class="lp-plan-price">9,99€ <small>/ mois</small></div>
            <div class="lp-plan-sub">Pour l'investisseur régulier</div>
            <ul class="lp-plan-feats">
              <li>Tous les actifs suivis</li>
              <li>Signaux IA illimités</li>
              <li>Alertes email illimitées</li>
              <li>Recommandations personnalisées</li>
            </ul>
            <div class="lp-plan-cta">Choisir Pro</div>
          </div>
          <div class="lp-plan">
            <div class="lp-plan-name">Premium</div>
            <div class="lp-plan-price">29,99€ <small>/ mois</small></div>
            <div class="lp-plan-sub">Pour aller plus loin</div>
            <ul class="lp-plan-feats">
              <li>Tout le plan Pro</li>
              <li>Coach IA illimité</li>
              <li>Backtest & analyses avancées</li>
              <li>Support prioritaire</li>
            </ul>
            <div class="lp-plan-cta">Choisir Premium</div>
          </div>
        </div>

        <div class="lp-foot">© 2026 MarketPilot · Plateforme cloud d'analyse temps réel des marchés financiers</div>
        """,
        unsafe_allow_html=True,
    )
