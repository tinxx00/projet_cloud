"""Theming, CSS injection, and reusable UI components for the dashboard."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#F6F3FC",
    "surface": "#FFFFFF",
    "surface_alt": "#F0EAFB",
    "border": "#E6DCF7",
    "text": "#3B3560",
    "text_muted": "#8983A6",
    "primary": "#8B5CF6",
    "primary_soft": "rgba(139, 92, 246, 0.12)",
    "up": "#059669",
    "up_soft": "rgba(5, 150, 105, 0.14)",
    "down": "#F43F5E",
    "down_soft": "rgba(244, 63, 94, 0.14)",
    "warn": "#D97706",
    "warn_soft": "rgba(217, 119, 6, 0.14)",
}


PLOTLY_TEMPLATE = "plotly_white"


def plotly_layout(**overrides) -> dict:
    """Layout par défaut pour les figures Plotly."""
    base = dict(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(color=COLORS["text"], family="Inter, system-ui, sans-serif"),
        xaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
        yaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"]),
        hoverlabel=dict(bgcolor=COLORS["surface"], font_size=12),
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

:root {{
    --bg: {COLORS["bg"]};
    --surface: {COLORS["surface"]};
    --surface-alt: {COLORS["surface_alt"]};
    --border: {COLORS["border"]};
    --text: {COLORS["text"]};
    --text-muted: {COLORS["text_muted"]};
    --primary: {COLORS["primary"]};
    --up: {COLORS["up"]};
    --down: {COLORS["down"]};
    --warn: {COLORS["warn"]};
}}

html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}}

/* Page padding */
.block-container {{
    padding-top: 2.2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1400px;
}}

/* Headings */
h1, h2, h3 {{
    letter-spacing: -0.01em;
    font-weight: 700 !important;
}}
h1 {{ font-size: 2rem !important; }}
h2 {{ font-size: 1.35rem !important; margin-top: 1.2rem !important; }}
h3 {{ font-size: 1.05rem !important; color: var(--text-muted) !important; }}

/* Sidebar polish */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F0EAFB 100%);
    border-right: 1px solid var(--border);
}}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 {{
    color: var(--text);
}}

/* Custom card */
.card {{
    background: linear-gradient(145deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 6px 20px rgba(139,92,246,0.08), 0 1px 0 rgba(255,255,255,0.6) inset;
    transition: transform 150ms cubic-bezier(.2,.8,.2,1), border-color 150ms ease, box-shadow 150ms ease;
    position: relative;
    overflow: hidden;
}}
.card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(168, 85, 247,0.3), transparent);
    opacity: 0;
    transition: opacity 150ms ease;
}}
.card:hover {{
    border-color: rgba(168, 85, 247, 0.5);
    transform: translateY(-3px);
    box-shadow: 0 12px 30px rgba(139,92,246,0.16), 0 0 0 1px rgba(139,92,246,0.12);
}}
.card:hover::before {{ opacity: 1; }}

.card-title {{
    color: var(--text-muted);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}}
.card-value {{
    color: var(--text);
    font-size: 1.65rem;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
}}
.card-sub {{
    color: var(--text-muted);
    font-size: 0.82rem;
    margin-top: 0.35rem;
}}
.card-delta-up   {{ color: var(--up);   font-weight: 700; }}
.card-delta-down {{ color: var(--down); font-weight: 700; }}
.card-delta-flat {{ color: var(--text-muted); font-weight: 600; }}

/* Gradient text */
.gtext {{
    background: linear-gradient(135deg, #A855F7 0%, #E879F9 50%, #F0ABFC 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

/* Hero header */
.hero {{
    background:
        radial-gradient(ellipse 80% 60% at 0% 0%, rgba(168, 85, 247,0.15) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 100% 100%, rgba(232, 121, 249,0.12) 0%, transparent 50%),
        linear-gradient(180deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1.8rem 2rem;
    margin-bottom: 1.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    position: relative;
    overflow: hidden;
}}
.hero::after {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(168, 85, 247,0.6) 50%, transparent 100%);
}}
.hero-title {{
    font-size: 1.75rem;
    font-weight: 900;
    margin: 0;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #7C3AED 0%, #DB2777 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.hero-subtitle {{ color: var(--text-muted); font-size: 0.95rem; margin-top: 0.4rem; line-height: 1.5; }}

/* Status pill */
.pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.35rem 0.8rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    border: 1px solid var(--border);
    background: rgba(139, 92, 246, 0.05);
    letter-spacing: 0.04em;
}}
.pill-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    animation: pulse 1.8s ease-in-out infinite;
}}
.pill-live    {{ color: var(--up);   border-color: rgba(16,185,129,0.5); background: rgba(16,185,129,0.08); }}
.pill-live   .pill-dot {{ background: var(--up); box-shadow: 0 0 6px var(--up); }}
.pill-idle    {{ color: var(--warn); border-color: rgba(245,158,11,0.5);  background: rgba(245,158,11,0.08); }}
.pill-idle   .pill-dot {{ background: var(--warn); }}
.pill-offline {{ color: var(--down); border-color: rgba(239,68,68,0.5);  background: rgba(239,68,68,0.08); }}
.pill-offline .pill-dot {{ background: var(--down); animation: none; }}

@keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50%       {{ opacity: 0.4; transform: scale(0.85); }}
}}

/* Architecture flow */
.arch-flow {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    flex-wrap: wrap;
    padding: 1.2rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    margin: 1rem 0;
}}
.arch-node {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.3rem;
    padding: 0.7rem 1rem;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: 12px;
    min-width: 90px;
    transition: all 150ms ease;
}}
.arch-node:hover {{
    border-color: rgba(168, 85, 247,0.6);
    background: rgba(168, 85, 247,0.06);
    transform: translateY(-2px);
}}
.arch-node-icon {{ font-size: 1.5rem; }}
.arch-node-label {{ font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }}
.arch-node-tech {{ font-size: 0.68rem; color: var(--primary); font-weight: 600; }}
.arch-arrow {{
    color: var(--primary);
    font-size: 1.2rem;
    padding: 0 0.2rem;
    opacity: 0.6;
    flex-shrink: 0;
}}

/* Ticker row */
.ticker-row {{
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}}
.ticker-item {{
    flex: 1 1 160px;
    background: linear-gradient(145deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.9rem 1.1rem;
    position: relative;
    overflow: hidden;
    transition: all 150ms ease;
}}
.ticker-item:hover {{ border-color: rgba(168, 85, 247,0.45); transform: translateY(-2px); }}
.ticker-sym {{ font-size: 0.75rem; font-weight: 800; color: var(--text-muted); letter-spacing: 0.1em; text-transform: uppercase; }}
.ticker-price {{ font-size: 1.4rem; font-weight: 800; color: var(--text); letter-spacing: -0.02em; margin: 0.15rem 0; }}
.ticker-up   {{ color: var(--up);   font-size: 0.82rem; font-weight: 700; }}
.ticker-down {{ color: var(--down); font-size: 0.82rem; font-weight: 700; }}
.ticker-bar {{
    position: absolute;
    bottom: 0; left: 0;
    height: 3px;
    border-radius: 0 0 0 14px;
    transition: width 600ms ease;
}}

/* Model comparison bar */
.model-row {{
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid rgba(39,49,77,0.5);
}}
.model-row:last-child {{ border-bottom: none; }}
.model-name {{ font-size: 0.82rem; font-weight: 700; min-width: 80px; color: var(--text); }}
.model-bar-wrap {{ flex: 1; background: rgba(255,255,255,0.04); border-radius: 6px; height: 10px; overflow: hidden; }}
.model-bar {{ height: 100%; border-radius: 6px; transition: width 800ms cubic-bezier(.2,.8,.2,1); }}
.model-auc {{ font-size: 0.82rem; font-weight: 700; min-width: 50px; text-align: right; }}
.model-best {{ color: var(--up); }}

/* Navigation feature cards */
.feat-card {{
    background: linear-gradient(145deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.3rem 1.4rem;
    height: 100%;
    transition: all 180ms ease;
    cursor: default;
    position: relative;
    overflow: hidden;
}}
.feat-card:hover {{
    border-color: rgba(168, 85, 247,0.5);
    transform: translateY(-4px);
    box-shadow: 0 14px 34px rgba(139,92,246,0.18);
}}
.feat-card-emoji {{ font-size: 2rem; margin-bottom: 0.5rem; }}
.feat-card-title {{ font-size: 1rem; font-weight: 800; color: var(--text); margin-bottom: 0.3rem; }}
.feat-card-desc {{ font-size: 0.82rem; color: var(--text-muted); line-height: 1.5; }}

/* Proba gauge */
.gauge-wrap {{
    text-align: center;
    padding: 1.2rem;
}}
.gauge-value {{
    font-size: 3rem;
    font-weight: 900;
    letter-spacing: -0.04em;
    line-height: 1;
}}
.gauge-label {{
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-top: 0.4rem;
}}

/* Badge for direction */
.badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.6rem;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}}
.badge-up   {{ color: var(--up);   background: {COLORS["up_soft"]}; border: 1px solid rgba(16,185,129,0.3); }}
.badge-down {{ color: var(--down); background: {COLORS["down_soft"]}; border: 1px solid rgba(239,68,68,0.3); }}
.badge-flat {{ color: var(--text-muted); background: rgba(148,163,184,0.12); border: 1px solid rgba(148,163,184,0.2); }}
.badge-flat-primary {{ color: var(--primary); background: rgba(168, 85, 247,0.1); border: 1px solid rgba(168, 85, 247,0.3); }}

/* Section header */
.section-head {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0.6rem 0 0.8rem 0;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid var(--border);
}}
.section-head h2 {{ margin: 0 !important; }}

/* Tab styling */
button[data-baseweb="tab"] {{
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
}}

/* Streamlit metrics enhancements */
[data-testid="stMetric"] {{
    background: linear-gradient(145deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1rem 1.2rem;
    transition: all 150ms ease;
}}
[data-testid="stMetric"]:hover {{
    border-color: rgba(168, 85, 247,0.4);
}}
[data-testid="stMetricLabel"] {{
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 600 !important;
}}
[data-testid="stMetricValue"] {{
    font-weight: 800 !important;
    font-size: 1.7rem !important;
    letter-spacing: -0.02em !important;
}}

/* Buttons */
button[kind="primary"], .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #7C3AED 0%, #A855F7 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 14px rgba(139, 92, 246,0.35) !important;
}}
.stButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 150ms ease !important;
}}

/* DataFrame */
[data-testid="stDataFrame"] {{
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
}}

/* Expander */
[data-testid="stExpander"] {{
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    background: var(--surface) !important;
}}

/* Inputs */
.stTextInput input, .stNumberInput input {{
    border-radius: 10px !important;
    background: var(--surface-alt) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}}
.stSelectbox > div {{ border-radius: 10px !important; }}
.stMultiSelect [data-baseweb="select"] {{ border-radius: 10px !important; }}

/* Divider */
hr {{ border-color: var(--border) !important; margin: 1.2rem 0 !important; }}

/* Reduce gap */
.element-container {{ margin-bottom: 0.6rem; }}

/* Streamlit progress bar */
.stProgress > div > div {{ border-radius: 999px !important; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--text-muted); }}

/* Toast */
[data-testid="stToast"] {{ border-radius: 12px !important; }}

/* ── Aurora background (subtil, sur toutes les pages) ──────────────────── */
[data-testid="stAppViewContainer"] {{
    background:
        radial-gradient(ellipse 55% 45% at 8% -8%, rgba(196,181,253,0.50) 0%, transparent 55%),
        radial-gradient(ellipse 50% 42% at 98% 4%, rgba(249,168,212,0.42) 0%, transparent 55%),
        radial-gradient(ellipse 60% 50% at 55% 110%, rgba(167,243,208,0.30) 0%, transparent 55%),
        var(--bg);
    background-attachment: fixed;
}}

/* ── Animation d'entrée (éléments statiques uniquement) ───────────────── */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.hero, .feat-card, .auth-panel, .arch-flow, .landing-brand, .landing-h1, .landing-lead {{
    animation: fadeInUp 480ms cubic-bezier(.2,.8,.2,1) both;
}}
.feat-card:nth-child(2) {{ animation-delay: 60ms; }}
.feat-card:nth-child(3) {{ animation-delay: 120ms; }}

/* ── Navigation sidebar : hover + onglet actif ────────────────────────── */
[data-testid="stSidebarNav"] ul {{ gap: 2px; }}
[data-testid="stSidebarNavLink"] {{
    border-radius: 10px !important;
    padding: 0.5rem 0.7rem !important;
    border: 1px solid transparent !important;
    transition: background 140ms ease, border-color 140ms ease !important;
}}
[data-testid="stSidebarNavLink"]:hover {{
    background: rgba(168, 85, 247,0.08) !important;
    border-color: rgba(168, 85, 247,0.20) !important;
}}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: linear-gradient(135deg, rgba(168, 85, 247,0.18), rgba(232, 121, 249,0.12)) !important;
    border-color: rgba(168, 85, 247,0.35) !important;
}}
[data-testid="stSidebarNavLink"][aria-current="page"] span {{
    color: var(--text) !important; font-weight: 700 !important;
}}

/* ── Boutons primaires : glow au survol ───────────────────────────────── */
button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {{
    filter: brightness(1.08);
    transform: translateY(-1px);
    box-shadow: 0 6px 22px rgba(168, 85, 247,0.45) !important;
}}

/* ── Barre d'accent sur les titres de section ─────────────────────────── */
.section-head h2 {{ position: relative; padding-left: 0.7rem; }}
.section-head h2::before {{
    content: ''; position: absolute; left: 0; top: 14%; bottom: 14%;
    width: 3px; border-radius: 3px;
    background: linear-gradient(180deg, #A855F7, #E879F9);
}}

/* ── Logo / marque ────────────────────────────────────────────────────── */
.brand-mark {{
    width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
    background: linear-gradient(135deg, #8B5CF6 0%, #DB2777 100%);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 8px 20px rgba(139,92,246,0.35);
}}
.brand-name {{
    font-size: 1.5rem; font-weight: 900; letter-spacing: -0.02em; line-height: 1;
    background: linear-gradient(135deg, #7C3AED, #DB2777);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}}
.brand-tag {{ font-size: 0.72rem; color: var(--text-muted); letter-spacing: 0.14em; text-transform: uppercase; margin-top: 0.15rem; }}

/* ── Grille de tuiles uniformes ───────────────────────────────────────── */
.tile-grid {{ display: grid; gap: 0.9rem; margin-bottom: 0.5rem; }}
.tile-grid.cols-4 {{ grid-template-columns: repeat(4, 1fr); }}
.tile-grid.cols-5 {{ grid-template-columns: repeat(5, 1fr); }}

.tile {{
    background: linear-gradient(150deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border); border-radius: 16px;
    padding: 1.05rem 1.15rem; min-height: 116px;
    display: flex; flex-direction: column; gap: 0.2rem;
    box-shadow: 0 4px 16px rgba(139,92,246,0.06);
    transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
}}
.tile:hover {{ transform: translateY(-3px); border-color: rgba(139,92,246,0.45);
    box-shadow: 0 12px 26px rgba(139,92,246,0.14); }}
.tile-label {{ font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.07em; color: var(--text-muted); }}
.tile-value {{ font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em; color: var(--text); line-height: 1.15; }}
.tile-sub {{ font-size: 0.77rem; color: var(--text-muted); margin-top: auto; }}

/* Tuile "lanceur d'application" */
.app-tile {{
    background: linear-gradient(150deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border); border-radius: 16px;
    padding: 1.1rem; min-height: 138px;
    display: flex; flex-direction: column; gap: 0.5rem;
    box-shadow: 0 4px 16px rgba(139,92,246,0.06);
    transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
}}
.app-tile:hover {{ transform: translateY(-4px); border-color: rgba(139,92,246,0.5);
    box-shadow: 0 14px 30px rgba(139,92,246,0.16); }}
.app-ic {{ width: 40px; height: 40px; border-radius: 12px; display: flex;
    align-items: center; justify-content: center; font-size: 1.25rem; }}
.app-t {{ font-size: 0.95rem; font-weight: 800; color: var(--text); }}
.app-d {{ font-size: 0.76rem; color: var(--text-muted); line-height: 1.4; }}

@media (max-width: 1100px) {{
    .tile-grid.cols-4, .tile-grid.cols-5 {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* ── Logo sidebar (st.logo) ────────────────────────────────────────────── */
[data-testid="stLogo"] {{
    height: 2.5rem !important; width: auto !important;
    margin: 0.4rem 0 0.4rem 0.15rem !important;
}}
[data-testid="stSidebarHeader"] {{
    padding-top: 0.6rem !important; padding-bottom: 0.2rem !important;
}}

/* Hide footer */
footer {{ visibility: hidden; }}
</style>
"""


def inject_theme() -> None:
    """Inject the global CSS once per page run."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
def hero(title: str, subtitle: str, status: str = "live", last_update: datetime | None = None) -> None:
    """Render a hero header with title, subtitle, status pill, and last-update timestamp."""
    pill_class, label = {
        "live": ("pill-live", "LIVE"),
        "idle": ("pill-idle", "IDLE"),
        "offline": ("pill-offline", "OFFLINE"),
    }.get(status, ("pill-idle", "UNKNOWN"))

    if last_update is not None:
        ts = last_update.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        ts = "n/a"

    st.markdown(
        f"""
        <div class="hero">
          <div>
            <h1 class="hero-title">{title}</h1>
            <div class="hero-subtitle">{subtitle}</div>
          </div>
          <div style="display:flex; gap:0.6rem; align-items:center; flex-wrap:wrap;">
            <span class="pill {pill_class}"><span class="pill-dot"></span>{label}</span>
            <span class="pill" style="color: var(--text-muted);">⏱ Mis à jour {ts}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(title: str, value: str, sub: str | None = None,
             delta: float | None = None, delta_format: str = "{:+.2f}%") -> None:
    """Render a metric card. Use inside a column."""
    delta_html = ""
    if delta is not None:
        cls = "card-delta-up" if delta > 0 else ("card-delta-down" if delta < 0 else "card-delta-flat")
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "•")
        delta_html = f'<div class="{cls}" style="font-size:0.85rem;margin-top:0.25rem;">{arrow} {delta_format.format(delta)}</div>'

    sub_html = f'<div class="card-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">{title}</div>
          <div class="card-value">{value}</div>
          {delta_html}
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def direction_badge(direction: str | None) -> str:
    """Return HTML for a direction badge."""
    if direction == "up":
        return '<span class="badge badge-up">▲ UP</span>'
    if direction == "down":
        return '<span class="badge badge-down">▼ DOWN</span>'
    if direction == "flat":
        return '<span class="badge badge-flat">• FLAT</span>'
    return '<span class="badge badge-flat">— N/A</span>'


def empty_state(emoji: str, title: str, message: str, action: str | None = None) -> None:
    """Friendly empty-state block."""
    action_html = f'<div style="margin-top:0.7rem;color:var(--primary);font-weight:600;">{action}</div>' if action else ""
    st.markdown(
        f"""
        <div class="card" style="text-align:center; padding: 2.2rem 1.4rem;">
          <div style="font-size:2.4rem;">{emoji}</div>
          <div style="font-size:1.1rem; font-weight:600; margin-top:0.4rem;">{title}</div>
          <div style="color:var(--text-muted); margin-top:0.3rem;">{message}</div>
          {action_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None, right: str | None = None) -> None:
    """Compact section heading with optional subtitle and right-side hint."""
    right_html = f'<span style="color:var(--text-muted);font-size:0.85rem;">{right}</span>' if right else ""
    sub_html = f'<div style="color:var(--text-muted);font-size:0.88rem;">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-head">
          <div>
            <h2>{title}</h2>
            {sub_html}
          </div>
          {right_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def freshness_status(last_update: datetime | None, idle_seconds: int = 30,
                     offline_seconds: int = 120) -> str:
    """Compute live/idle/offline status from a timestamp."""
    if last_update is None:
        return "offline"
    now = datetime.now(timezone.utc)
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)
    delta = (now - last_update).total_seconds()
    if delta < idle_seconds:
        return "live"
    if delta < offline_seconds:
        return "idle"
    return "offline"


def format_price(value: float | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}"


def format_pct(value: float | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:+.{decimals}f}%"


def colored_value(value: float | None, fmt: str = "{:+.2f}%") -> str:
    """Inline colored number for tables/metrics."""
    if value is None or pd.isna(value):
        return '<span style="color:var(--text-muted)">—</span>'
    color = COLORS["up"] if value > 0 else (COLORS["down"] if value < 0 else COLORS["text_muted"])
    return f'<span style="color:{color};font-weight:600">{fmt.format(value)}</span>'


def chip_row(items: Iterable[str]) -> None:
    """Inline chip row, useful to display selected symbols."""
    chips = "".join(
        f'<span class="badge badge-flat" style="margin-right:0.35rem;">{x}</span>'
        for x in items
    )
    st.markdown(f'<div style="margin-bottom:0.4rem;">{chips}</div>', unsafe_allow_html=True)
