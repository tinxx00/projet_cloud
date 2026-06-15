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
    "bg": "#0B1020",
    "surface": "#141A2E",
    "surface_alt": "#1B2238",
    "border": "#27314D",
    "text": "#E2E8F0",
    "text_muted": "#94A3B8",
    "primary": "#22D3EE",
    "primary_soft": "rgba(34, 211, 238, 0.18)",
    "up": "#10B981",
    "up_soft": "rgba(16, 185, 129, 0.16)",
    "down": "#EF4444",
    "down_soft": "rgba(239, 68, 68, 0.16)",
    "warn": "#F59E0B",
    "warn_soft": "rgba(245, 158, 11, 0.16)",
}


PLOTLY_TEMPLATE = "plotly_dark"


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
    background: linear-gradient(180deg, #0E1428 0%, #0B1020 100%);
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
    box-shadow: 0 4px 24px rgba(0,0,0,0.22), 0 1px 0 rgba(255,255,255,0.03) inset;
    transition: transform 150ms cubic-bezier(.2,.8,.2,1), border-color 150ms ease, box-shadow 150ms ease;
    position: relative;
    overflow: hidden;
}}
.card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(34,211,238,0.3), transparent);
    opacity: 0;
    transition: opacity 150ms ease;
}}
.card:hover {{
    border-color: rgba(34, 211, 238, 0.5);
    transform: translateY(-3px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), 0 0 0 1px rgba(34,211,238,0.1);
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
    background: linear-gradient(135deg, #22D3EE 0%, #818CF8 50%, #A78BFA 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

/* Hero header */
.hero {{
    background:
        radial-gradient(ellipse 80% 60% at 0% 0%, rgba(34,211,238,0.15) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 100% 100%, rgba(129,140,248,0.12) 0%, transparent 50%),
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
    background: linear-gradient(90deg, transparent 0%, rgba(34,211,238,0.6) 50%, transparent 100%);
}}
.hero-title {{
    font-size: 1.75rem;
    font-weight: 900;
    margin: 0;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #E2E8F0 0%, #94A3B8 100%);
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
    background: rgba(255, 255, 255, 0.03);
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
    border-color: rgba(34,211,238,0.6);
    background: rgba(34,211,238,0.06);
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
.ticker-item:hover {{ border-color: rgba(34,211,238,0.45); transform: translateY(-2px); }}
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
    border-color: rgba(34,211,238,0.5);
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.3);
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
.badge-flat-primary {{ color: var(--primary); background: rgba(34,211,238,0.1); border: 1px solid rgba(34,211,238,0.3); }}

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
    border-color: rgba(34,211,238,0.4);
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
    background: linear-gradient(135deg, #0EA5E9 0%, #22D3EE 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    color: #0B1020 !important;
    box-shadow: 0 4px 14px rgba(34,211,238,0.3) !important;
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
