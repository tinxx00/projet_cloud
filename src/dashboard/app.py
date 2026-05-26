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
    page_title="Market Platform",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Market Platform — Projet Cloud FinTech temps réel.",
    },
)

# ── Auth gate ─────────────────────────────────────────────────────────────────
theme.inject_css()
if not auth.is_logged_in():
    auth.render_login_page()
    st.stop()

# ── Pages ─────────────────────────────────────────────────────────────────────
VIEWS_DIR = _HERE.parent / "views"

user = auth.current_user()

pages = {
    "home":      st.Page(str(VIEWS_DIR / "home.py"),      title="Accueil",         icon="🏠", default=True),
    "market":    st.Page(str(VIEWS_DIR / "market.py"),    title="Marché",          icon="📈"),
    "analysis":  st.Page(str(VIEWS_DIR / "analysis.py"),  title="Analyse",         icon="🔬"),
    "pipeline":  st.Page(str(VIEWS_DIR / "pipeline.py"),  title="Pipeline",        icon="⚙️"),
    "recommend": st.Page(str(VIEWS_DIR / "recommend.py"), title="Recommandations", icon="🎯"),
    "ml":        st.Page(str(VIEWS_DIR / "ml.py"),        title="Signal IA",       icon="🤖"),
    "profile":   st.Page(str(VIEWS_DIR / "profile.py"),   title="Mon Profil",      icon="👤"),
    "guide":     st.Page(str(VIEWS_DIR / "guide.py"),     title="Guide",           icon="📚"),
    "about":     st.Page(str(VIEWS_DIR / "about.py"),     title="À propos",        icon="ℹ️"),
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:0.6rem;padding:0.4rem 0 1rem 0;
                    border-bottom:1px solid #27314D;margin-bottom:0.8rem;">
          <div style="width:38px;height:38px;border-radius:10px;
                      background:linear-gradient(135deg,#22D3EE 0%,#0EA5E9 100%);
                      display:flex;align-items:center;justify-content:center;
                      font-size:1.3rem;">💹</div>
          <div>
            <div style="font-weight:800;font-size:1.05rem;line-height:1.1;">Market Platform</div>
            <div style="font-size:0.72rem;color:#94A3B8;letter-spacing:0.06em;
                        text-transform:uppercase;">Cloud · Real-time</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # User badge
    alerts_on = user.get("alerts", {}).get("enabled", False)
    alert_badge = "🔔" if alerts_on else "🔕"
    st.markdown(
        f"""<div style="background:#1B2238;border-radius:8px;padding:0.6rem 0.8rem;
                        margin-bottom:0.8rem;border:1px solid #27314D;">
              <div style="font-weight:700;font-size:0.9rem;">{alert_badge} {user['name']}</div>
              <div style="color:#94A3B8;font-size:0.75rem;">{user['email']}</div>
            </div>""",
        unsafe_allow_html=True,
    )

nav = st.navigation(
    {
        "Plateforme":       [pages["home"], pages["market"], pages["analysis"], pages["pipeline"]],
        "Personnalisation": [pages["recommend"], pages["profile"]],
        "Modèle":           [pages["ml"]],
        "Aide":             [pages["guide"], pages["about"]],
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
                    border-top:1px solid #27314D;padding-top:0.6rem;margin-top:0.5rem;">
          v1.1 · Streamlit · Plotly · Kafka · SageMaker
        </div>""",
        unsafe_allow_html=True,
    )
