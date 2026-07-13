"""Market Platform — Streamlit entry point.

Le dashboard est multi-pages via ``st.navigation``. Chaque page est un
module dans ``dashboard/views/`` et est exécutée à la sélection.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


# Make sure both `src/` and the project root are importable, regardless of
# whether streamlit is launched from the repo root or from `src/`.
_HERE = Path(__file__).resolve()
_SRC = _HERE.parents[1]
_ROOT = _HERE.parents[2]
for p in (_SRC, _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dashboard import auth
from dashboard import theme

st.set_page_config(
    page_title="MarketPilot",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "MarketPilot — Assistant intelligent pour investir avec confiance.",
    },
)

# ── Auth gate ─────────────────────────────────────────────────────────────────
theme.inject_theme()
if not auth.is_logged_in():
    auth.render_login_page()
    st.stop()

# ── Pages ─────────────────────────────────────────────────────────────────────
VIEWS_DIR = _HERE.parent / "views"

user = auth.current_user()

# ── Vérification alertes prix (toasts) ───────────────────────────────────────
_alerts_cfg = user.get("alerts") if user else None
if isinstance(_alerts_cfg, dict) and _alerts_cfg.get("enabled"):
    try:
        from dashboard import alerts as alerts_module
        from dashboard import data as data_module
        _df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
        if _df.empty:
            _df = data_module.load_quotes(data_module.RAW_DATA_PATH)
        _triggered = alerts_module.check_price_spikes(user, _df)
        for _a in _triggered:
            _emoji = "🚀" if _a["direction"] == "UP" else "🔻"
            _color = "success" if _a["direction"] == "UP" else "error"
            _msg = f"{_emoji} **{_a['symbol']}** — Pic {'hausse' if _a['direction'] == 'UP' else 'baisse'} détecté ({_a['pct']:+.2f}%)"
            if _color == "success":
                st.toast(_msg, icon="🚀")
            else:
                st.toast(_msg, icon="🔻")
    except Exception:
        pass

pages = {
    "home":      st.Page(str(VIEWS_DIR / "home.py"),        title="Accueil",         icon="🏠", default=True),
    "market":    st.Page(str(VIEWS_DIR / "market.py"),      title="Tendances",       icon="📈"),
    "analysis":  st.Page(str(VIEWS_DIR / "analysis.py"),    title="Opportunités",    icon="💡"),
    "assistant": st.Page(str(VIEWS_DIR / "assistant.py"),   title="Coach IA",        icon="💬"),
    "pipeline":  st.Page(str(VIEWS_DIR / "pipeline.py"),    title="Activité",        icon="⚙️"),
    "recommend": st.Page(str(VIEWS_DIR / "recommend.py"),   title="Recommandations", icon="🎯"),
    "ml":        st.Page(str(VIEWS_DIR / "ml.py"),          title="Assistant IA",    icon="🤖"),
    "alerts":    st.Page(str(VIEWS_DIR / "alerts_view.py"), title="Alertes",         icon="🔔"),
    "profile":   st.Page(str(VIEWS_DIR / "profile.py"),     title="Mon compte",      icon="👤"),
    "guide":     st.Page(str(VIEWS_DIR / "guide.py"),       title="Parcours",        icon="🧭"),
    "about":     st.Page(str(VIEWS_DIR / "about.py"),       title="Produit",         icon="✨"),
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
# Logo MarketPilot tout en haut de la sidebar (au-dessus de la navigation).
_LOGO_PATH = str(_HERE.parent / "assets" / "marketpilot_logo.svg")
try:
    st.logo(_LOGO_PATH, size="large")
except Exception:
    pass

with st.sidebar:
    # User badge
    alerts_on = user.get("alerts", {}).get("enabled", False)
    alert_badge = "🔔" if alerts_on else "🔕"
    st.markdown(
        f"""<div style="background:var(--surface-alt);border-radius:8px;padding:0.6rem 0.8rem;
                        margin-bottom:0.8rem;border:1px solid var(--border);">
              <div style="font-weight:700;font-size:0.9rem;color:var(--text);">{alert_badge} {user['name']}</div>
              <div style="color:var(--text-muted);font-size:0.75rem;">{user['email']}</div>
            </div>""",
        unsafe_allow_html=True,
    )

nav = st.navigation(
    {
        "Produit":          [pages["home"], pages["market"], pages["analysis"], pages["assistant"], pages["recommend"], pages["alerts"]],
        "Compte":           [pages["profile"]],
        "Insights avancés": [pages["ml"], pages["pipeline"]],
        "Ressources":       [pages["guide"], pages["about"]],
    },
    position="sidebar",
)
nav.run()

with st.sidebar:
    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    if st.button("🚪 Se déconnecter", use_container_width=True):
        auth.logout()
    st.markdown(
        """<div style="color:#64748B;font-size:0.72rem;text-align:center;
                    border-top:1px solid var(--border);padding-top:0.6rem;margin-top:0.5rem;">
                    MarketPilot · Version Démo commerciale
        </div>""",
        unsafe_allow_html=True,
    )
