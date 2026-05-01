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


VIEWS_DIR = _HERE.parent / "views"

pages = {
    "home":      st.Page(str(VIEWS_DIR / "home.py"),      title="Accueil",        icon="🏠", default=True),
    "market":    st.Page(str(VIEWS_DIR / "market.py"),    title="Marché",         icon="📈"),
    "analysis":  st.Page(str(VIEWS_DIR / "analysis.py"),  title="Analyse",        icon="🔬"),
    "pipeline":  st.Page(str(VIEWS_DIR / "pipeline.py"),  title="Pipeline",       icon="⚙️"),
    "recommend": st.Page(str(VIEWS_DIR / "recommend.py"), title="Recommandations",icon="🎯"),
    "ml":        st.Page(str(VIEWS_DIR / "ml.py"),        title="Signal IA",      icon="🤖"),
    "about":     st.Page(str(VIEWS_DIR / "about.py"),     title="À propos",       icon="ℹ️"),
}

# Sidebar header (rendered before navigation list)
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

nav = st.navigation(
    {
        "Plateforme": [pages["home"], pages["market"], pages["analysis"], pages["pipeline"]],
        "Personnalisation": [pages["recommend"]],
        "Modèle": [pages["ml"]],
        "Infos": [pages["about"]],
    },
    position="sidebar",
)
nav.run()


with st.sidebar:
    st.markdown(
        """
        <div style="position:absolute;bottom:1rem;left:1rem;right:1rem;
                    color:#64748B;font-size:0.72rem;text-align:center;
                    border-top:1px solid #27314D;padding-top:0.6rem;">
          v1.0 · Streamlit · Plotly · Kafka
        </div>
        """,
        unsafe_allow_html=True,
    )
