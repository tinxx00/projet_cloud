"""Authentication module — login/signup with email.

Stocke les utilisateurs dans ``data/users.json``.
Gère la session Streamlit et les préférences d'alertes.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

USERS_PATH = Path("data/users.json")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


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
        if u["email"] == email and u["password_hash"] == _hash(password):
            st.session_state["auth_user"] = u
            st.session_state["user_id"] = uid
            return True, ""
    return False, "Email ou mot de passe incorrect."


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


def update_alerts(uid: str, enabled: bool, symbols: list[str],
                  threshold_up: float, threshold_down: float) -> None:
    update_user(uid, {"alerts": {
        "enabled": enabled,
        "symbols": symbols,
        "threshold_up": threshold_up,
        "threshold_down": threshold_down,
    }})


def update_risk_pref(uid: str, pref: float) -> None:
    update_user(uid, {"risk_pref": pref})


# ─── Login/Signup UI ──────────────────────────────────────────────────────────

def render_login_page() -> None:
    """Renders the full login/signup page. Call from app.py when not logged in."""
    st.markdown("""
    <style>
    .auth-container { max-width: 420px; margin: 4rem auto; }
    .auth-title { font-size: 2rem; font-weight: 800; color: var(--primary); margin-bottom: 0.2rem; }
    .auth-sub { color: var(--text-muted); margin-bottom: 2rem; font-size: 0.95rem; }
    </style>
    <div class="auth-container">
      <div class="auth-title">💹 Market Platform</div>
      <div class="auth-sub">Plateforme d'analyse boursière temps réel</div>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        tab_login, tab_signup = st.tabs(["🔑 Connexion", "✨ Créer un compte"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="vous@exemple.com")
                password = st.text_input("Mot de passe", type="password")
                submitted = st.form_submit_button("Se connecter", use_container_width=True, type="primary")
            if submitted:
                ok, msg = login(email, password)
                if ok:
                    st.success("Connecté ! Bienvenue 👋")
                    st.rerun()
                else:
                    st.error(msg)

        with tab_signup:
            with st.form("signup_form"):
                name = st.text_input("Nom complet", placeholder="Marie Dupont")
                email2 = st.text_input("Email", placeholder="vous@exemple.com", key="su_email")
                password2 = st.text_input("Mot de passe", type="password", key="su_pw")
                password3 = st.text_input("Confirmer le mot de passe", type="password", key="su_pw2")
                submitted2 = st.form_submit_button("Créer mon compte", use_container_width=True, type="primary")
            if submitted2:
                if password2 != password3:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    ok, result = signup(name, email2, password2)
                    if ok:
                        # Auto-login after signup
                        login(email2, password2)
                        st.success("Compte créé ! Bienvenue 🎉")
                        st.rerun()
                    else:
                        st.error(result)
