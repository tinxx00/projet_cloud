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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

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
    background: linear-gradient(180deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    transition: transform 120ms ease, border-color 120ms ease;
}}
.card:hover {{
    border-color: rgba(34, 211, 238, 0.45);
    transform: translateY(-2px);
}}

.card-title {{
    color: var(--text-muted);
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.4rem;
}}
.card-value {{
    color: var(--text);
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.1;
}}
.card-sub {{
    color: var(--text-muted);
    font-size: 0.82rem;
    margin-top: 0.35rem;
}}
.card-delta-up {{ color: var(--up); font-weight: 600; }}
.card-delta-down {{ color: var(--down); font-weight: 600; }}
.card-delta-flat {{ color: var(--text-muted); font-weight: 600; }}

/* Hero header */
.hero {{
    background: radial-gradient(1200px 240px at 0% 0%, rgba(34,211,238,0.18), transparent 60%),
                linear-gradient(180deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
}}
.hero-title {{ font-size: 1.6rem; font-weight: 800; margin: 0; }}
.hero-subtitle {{ color: var(--text-muted); font-size: 0.95rem; margin-top: 0.3rem; }}

/* Status pill */
.pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.32rem 0.7rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    border: 1px solid var(--border);
    background: rgba(255, 255, 255, 0.02);
}}
.pill-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    box-shadow: 0 0 0 4px rgba(255,255,255,0.04);
    animation: pulse 1.6s ease-in-out infinite;
}}
.pill-live   {{ color: var(--up);   border-color: rgba(16,185,129,0.4); }}
.pill-live  .pill-dot {{ background: var(--up); }}
.pill-idle   {{ color: var(--warn); border-color: rgba(245,158,11,0.4); }}
.pill-idle  .pill-dot {{ background: var(--warn); }}
.pill-offline{{ color: var(--down); border-color: rgba(239,68,68,0.4); }}
.pill-offline .pill-dot {{ background: var(--down); animation: none; }}

@keyframes pulse {{
    0% {{ opacity: 1; }} 50% {{ opacity: 0.45; }} 100% {{ opacity: 1; }}
}}

/* Badge for direction */
.badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.18rem 0.55rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}}
.badge-up   {{ color: var(--up);   background: {COLORS["up_soft"]}; }}
.badge-down {{ color: var(--down); background: {COLORS["down_soft"]}; }}
.badge-flat {{ color: var(--text-muted); background: rgba(148,163,184,0.16); }}

/* Section header (compact) */
.section-head {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0.4rem 0 0.6rem 0;
}}
.section-head h2 {{ margin: 0 !important; }}

/* Tab styling */
button[data-baseweb="tab"] {{
    font-weight: 600 !important;
    letter-spacing: 0.01em;
}}

/* Streamlit metrics enhancements */
[data-testid="stMetric"] {{
    background: linear-gradient(180deg, var(--surface) 0%, var(--surface-alt) 100%);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
}}
[data-testid="stMetricLabel"] {{
    color: var(--text-muted) !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
[data-testid="stMetricValue"] {{
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}}

/* Buttons */
button[kind="primary"], .stButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
}}

/* DataFrame */
[data-testid="stDataFrame"] {{
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}}

/* Expander */
[data-testid="stExpander"] {{
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
}}

/* Input rounding */
.stTextInput input, .stSelectbox > div, .stNumberInput input,
.stMultiSelect [data-baseweb="select"], .stSlider {{
    border-radius: 10px !important;
}}

/* Reduce gap between elements */
.element-container {{ margin-bottom: 0.75rem; }}

/* Hide default footer & menu, keep clean */
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
