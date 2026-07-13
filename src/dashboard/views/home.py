"""Home — dashboard d'accueil : logo, tuiles uniformes, lanceur d'application."""
from __future__ import annotations

import time
from datetime import timezone

import streamlit as st

from dashboard import data as data_module
from dashboard import theme


# Logo SVG (courbe haussière) — blanc sur le dégradé de la marque
_LOGO_SVG = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<path d="M3 15.5L8.5 10l4 3.5L21 5" stroke="white" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M15 5h6v6" stroke="white" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)

# Lanceur d'application : (icône, titre, description, couleur)
_APPS = [
    ("📈", "Tendances",       "Mouvements & performances du marché", "#8B5CF6"),
    ("💡", "Opportunités",    "Fenêtres d'entrée et zones à risque", "#A855F7"),
    ("🎯", "Recommandations", "Suggestions selon ton profil",        "#DB2777"),
    ("🤖", "Assistant IA",    "Signaux ML expliqués simplement",     "#059669"),
    ("💬", "Coach IA",        "Discute stratégie avec l'IA",         "#6366F1"),
    ("🔔", "Alertes",         "Notifications email en temps réel",    "#F43F5E"),
    ("⚙️", "Activité",        "Santé du pipeline de données",        "#D97706"),
    ("👤", "Mon compte",      "Profil, risque et préférences",       "#7C3AED"),
]


def _header(pill_html: str, ts_str: str) -> None:
    st.markdown(
        f"""<div class="hero">
          <div style="display:flex;align-items:center;gap:0.85rem;">
            <div class="brand-mark">{_LOGO_SVG}</div>
            <div>
              <div class="brand-name">MarketPilot</div>
              <div class="brand-tag">Invest smarter · Analyse temps réel</div>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.4rem;">
            {pill_html}
            <span style="color:var(--text-muted);font-size:0.78rem;">⏱ {ts_str}</span>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _kpi_tiles(proc_rows: int, raw_rows: int, symbols: list[str], last) -> None:
    if last:
        delta_s = (data_module.now_utc() - last).total_seconds()
        age = f"il y a {delta_s:.0f}s" if delta_s < 60 else f"il y a {delta_s/60:.1f} min"
    else:
        age = "—"
    syms_sub = " · ".join(symbols[:4]) + ("…" if len(symbols) > 4 else "") if symbols else "—"
    tiles = [
        ("Signaux analysés", f"{proc_rows:,}", "Analyse IA en continu"),
        ("Données marché",   f"{raw_rows:,}",  "Flux temps réel"),
        ("Actifs suivis",    str(len(symbols)), syms_sub),
        ("Dernière MàJ",     age,              "Marché en direct"),
    ]
    cells = "".join(
        f'<div class="tile"><div class="tile-label">{lbl}</div>'
        f'<div class="tile-value">{val}</div><div class="tile-sub">{sub}</div></div>'
        for lbl, val, sub in tiles
    )
    st.markdown(f'<div class="tile-grid cols-4">{cells}</div>', unsafe_allow_html=True)


def _ticker_tiles(df) -> None:
    SYMBOLS = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
    price_col = "price_current" if "price_current" in df.columns else "price"
    sym_col = "symbol" if "symbol" in df.columns else None
    cells = ""
    for sym in SYMBOLS:
        sub = None
        if sym_col and not df.empty:
            sub = df[df[sym_col] == sym][price_col].dropna().astype(float)
        if sub is not None and len(sub) >= 2:
            last = sub.iloc[-1]
            prev = sub.iloc[max(0, len(sub) - 20)]
            pct = (last - prev) / (prev + 1e-9) * 100
            up = pct >= 0
            color = theme.COLORS["up"] if up else theme.COLORS["down"]
            arrow = "▲" if up else "▼"
            bar_w = min(int(abs(pct) * 40), 100)
            price_str = f"${last:,.2f}"
            pct_str = f"{arrow} {abs(pct):.2f}%"
            cls = "ticker-up" if up else "ticker-down"
        else:
            color, bar_w, price_str, pct_str, cls = theme.COLORS["text_muted"], 0, "—", "—", "ticker-up"
        cells += (
            f'<div class="ticker-item"><div class="ticker-sym">{sym}</div>'
            f'<div class="ticker-price">{price_str}</div>'
            f'<div class="{cls}">{pct_str}</div>'
            f'<div class="ticker-bar" style="width:{bar_w}%;background:{color};opacity:0.75;"></div></div>'
        )
    st.markdown(f'<div class="tile-grid cols-5">{cells}</div>', unsafe_allow_html=True)


def _app_launcher() -> None:
    cells = ""
    for emoji, title, desc, color in _APPS:
        cells += (
            f'<div class="app-tile">'
            f'<div class="app-ic" style="background:{color}22;">{emoji}</div>'
            f'<div class="app-t">{title}</div>'
            f'<div class="app-d">{desc}</div></div>'
        )
    st.markdown(f'<div class="tile-grid cols-4">{cells}</div>', unsafe_allow_html=True)


def _render_architecture() -> None:
    nodes = [
        ("🌍", "Marché", "Données live"),
        ("📡", "Capture", "Temps réel"),
        ("🧠", "Analyse IA", "Signaux"),
        ("🎯", "Conseils", "Personnalisés"),
        ("🔔", "Alertes", "Instantanées"),
        ("📈", "Décision", "Investir"),
    ]
    html = '<div class="arch-flow">'
    for i, (icon, label, tech) in enumerate(nodes):
        html += (f'<div class="arch-node"><div class="arch-node-icon">{icon}</div>'
                 f'<div class="arch-node-label">{label}</div>'
                 f'<div class="arch-node-tech">{tech}</div></div>')
        if i < len(nodes) - 1:
            html += '<div class="arch-arrow">→</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _render_pipeline(raw_status, proc_status) -> None:
    for label, status in [("Flux marché", raw_status), ("Analyse en direct", proc_status)]:
        sub_status = theme.freshness_status(status.last_update)
        pill = {
            "live":    '<span class="pill pill-live"><span class="pill-dot"></span>LIVE</span>',
            "idle":    '<span class="pill pill-idle"><span class="pill-dot"></span>IDLE</span>',
            "offline": '<span class="pill pill-offline"><span class="pill-dot"></span>OFFLINE</span>',
        }[sub_status]
        ts = status.last_update.astimezone(timezone.utc).strftime("%H:%M:%S UTC") if status.last_update else "—"
        st.markdown(
            f"""<div class="card" style="margin-bottom:0.7rem;">
              <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.3rem;">
                <span class="card-title" style="margin:0;">{label}</span>{pill}
              </div>
              <div style="font-size:1.35rem;font-weight:800;color:var(--text);">{status.rows:,}
                <span style="font-size:0.8rem;font-weight:500;color:var(--text-muted);">signaux</span>
              </div>
              <div class="card-sub">Màj : {ts}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def render() -> None:
    theme.inject_theme()

    raw_status  = data_module.dataset_status(data_module.RAW_DATA_PATH)
    proc_status = data_module.dataset_status(data_module.PROCESSED_DATA_PATH)
    last = max([s.last_update for s in (raw_status, proc_status) if s.last_update], default=None)
    pipe_status = theme.freshness_status(last, idle_seconds=30, offline_seconds=180)

    pill_html = {
        "live":    '<span class="pill pill-live"><span class="pill-dot"></span>PIPELINE LIVE</span>',
        "idle":    '<span class="pill pill-idle"><span class="pill-dot"></span>PIPELINE IDLE</span>',
        "offline": '<span class="pill pill-offline"><span class="pill-dot"></span>PIPELINE OFFLINE</span>',
    }[pipe_status]
    ts_str = last.astimezone(timezone.utc).strftime("%d %b %Y · %H:%M:%S UTC") if last else "—"

    _header(pill_html, ts_str)

    df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    if df.empty:
        df = data_module.load_quotes(data_module.RAW_DATA_PATH)
    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []

    # ── Rangée 1 : KPIs (tuiles identiques) ──────────────────────────────
    _kpi_tiles(proc_status.rows, raw_status.rows, symbols, last)

    # ── Rangée 2 : cours en direct (tuiles identiques) ───────────────────
    theme.section_header("📡 Cours en direct", "Variation sur les derniers ticks")
    _ticker_tiles(df)

    # ── Rangée 3 : lanceur d'application (carreaux identiques) ────────────
    theme.section_header("🚀 Explorer l'application", "Tout ce que MarketPilot met à ta disposition")
    _app_launcher()

    # ── Rangée 4 : simulateur de valeur + état du service ────────────────
    st.write("")
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        theme.section_header("💸 Simulateur de valeur", "Projection simple du ROI client")
        c1, c2 = st.columns(2)
        with c1:
            portefeuille = st.slider("Capital suivi (€)", 5_000, 500_000, 30_000, 1_000)
        with c2:
            niveau = st.selectbox("Profil client", ["Prudent", "Équilibré", "Dynamique"], index=1)
        gain_base = {"Prudent": 0.03, "Équilibré": 0.06, "Dynamique": 0.09}[niveau]
        gain_estime = portefeuille * gain_base
        economie_h = {"Prudent": 4, "Équilibré": 8, "Dynamique": 12}[niveau]
        tiles = [
            ("Gain potentiel / an", f"{gain_estime:,.0f} €", f"Hypothèse {gain_base*100:.0f}%"),
            ("Temps économisé / mois", f"{economie_h} h", "Alertes + IA + synthèse"),
            ("Décisions assistées", "24/7", "Coach IA en continu"),
        ]
        cells = "".join(
            f'<div class="tile"><div class="tile-label">{l}</div>'
            f'<div class="tile-value">{v}</div><div class="tile-sub">{s}</div></div>'
            for l, v, s in tiles
        )
        st.markdown(
            f'<div class="tile-grid" style="grid-template-columns:repeat(3,1fr);">{cells}</div>',
            unsafe_allow_html=True,
        )
    with right:
        theme.section_header("📶 État du service")
        _render_pipeline(raw_status, proc_status)
        if not raw_status.exists and not proc_status.exists:
            theme.empty_state("🚀", "Service en préparation",
                              "Les données arrivent bientôt.", "Synchronisation en cours")

    # ── Rangée 5 : parcours produit ──────────────────────────────────────
    st.write("")
    theme.section_header("🧭 Parcours produit", "De la donnée brute à la décision d'investissement")
    _render_architecture()

    if pipe_status == "live":
        time.sleep(5)
        st.rerun()


render()
