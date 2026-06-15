"""Home — page d'accueil avec ticker live, architecture et navigation."""
from __future__ import annotations

import time
from datetime import timezone

import streamlit as st

from dashboard import data as data_module
from dashboard import theme


def _render_ticker(df):
    SYMBOLS = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
    price_col = "price_current" if "price_current" in df.columns else "price"
    sym_col   = "symbol" if "symbol" in df.columns else None
    cols = st.columns(len(SYMBOLS))
    for i, sym in enumerate(SYMBOLS):
        if sym_col and not df.empty:
            sub = df[df[sym_col] == sym][price_col].dropna().astype(float)
        else:
            sub = df[price_col].dropna().astype(float) if not df.empty and price_col in df.columns else None
        if sub is not None and len(sub) >= 2:
            last  = sub.iloc[-1]
            prev  = sub.iloc[max(0, len(sub) - 20)]
            pct   = (last - prev) / (prev + 1e-9) * 100
            up    = pct >= 0
            color = "#10B981" if up else "#EF4444"
            arrow = "▲" if up else "▼"
            bar_w = min(int(abs(pct) * 40), 100)
        else:
            last, pct, color, arrow, bar_w = None, None, "#94A3B8", "•", 0
        with cols[i]:
            price_str = f"${last:,.2f}" if last else "—"
            pct_str   = f"{arrow} {abs(pct):.2f}%" if pct is not None else "—"
            cls = "ticker-up" if pct and pct >= 0 else "ticker-down"
            st.markdown(
                f"""<div class="ticker-item">
                    <div class="ticker-sym">{sym}</div>
                    <div class="ticker-price">{price_str}</div>
                    <div class="{cls}">{pct_str}</div>
                    <div class="ticker-bar" style="width:{bar_w}%;background:{color};opacity:0.7;"></div>
                </div>""",
                unsafe_allow_html=True,
            )


def _render_architecture():
    nodes = [
        ("🌐", "Finnhub", "API REST"),
        ("⚡", "Producer", "Kafka"),
        ("📨", "Kafka", "AWS EC2"),
        ("⚙️", "Consumer", "Traitement"),
        ("🗄️", "S3 / CSV", "Stockage"),
        ("🤖", "ML Engine", "9 modèles"),
        ("💹", "Dashboard", "Streamlit"),
    ]
    html = '<div class="arch-flow">'
    for i, (icon, label, tech) in enumerate(nodes):
        html += f'<div class="arch-node"><div class="arch-node-icon">{icon}</div><div class="arch-node-label">{label}</div><div class="arch-node-tech">{tech}</div></div>'
        if i < len(nodes) - 1:
            html += '<div class="arch-arrow">→</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _render_nav_cards():
    cards = [
        ("📈", "Marché temps réel",   "Chandeliers OHLC, KPIs et prix live. Rafraîchissement auto toutes les 5s.",      "#22D3EE"),
        ("🔬", "Analyse",             "Distributions, variations, leaderboard haussier/baissier par symbole.",            "#818CF8"),
        ("⚙️", "Pipeline",            "Flux Finnhub → Kafka → Consumer avec latences et métriques d'ingestion.",         "#F59E0B"),
        ("🤖", "Signal IA",           "9 modèles ML + AutoML Optuna, backtest complet et prédiction live.",              "#10B981"),
        ("🎯", "Recommandations",     "Moteur adaptatif qui apprend ton profil de risque via le feedback.",              "#A78BFA"),
        ("🔔", "Alertes",             "Notifications email automatiques sur pics de hausse ou baisse détectés.",          "#EF4444"),
    ]
    for row_start in range(0, len(cards), 3):
        cols = st.columns(3)
        for j, (emoji, title, desc, color) in enumerate(cards[row_start:row_start+3]):
            with cols[j]:
                st.markdown(
                    f"""<div class="feat-card" style="border-top:3px solid {color}44;margin-bottom:0.8rem;">
                        <div class="feat-card-emoji">{emoji}</div>
                        <div class="feat-card-title">{title}</div>
                        <div class="feat-card-desc">{desc}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )


def _render_pipeline(raw_status, proc_status):
    for label, status in [("Producer CSV brut", raw_status), ("Consumer CSV traité", proc_status)]:
        sub_status = theme.freshness_status(status.last_update)
        pill = {
            "live":    '<span class="pill pill-live"><span class="pill-dot"></span>LIVE</span>',
            "idle":    '<span class="pill pill-idle"><span class="pill-dot"></span>IDLE</span>',
            "offline": '<span class="pill pill-offline"><span class="pill-dot"></span>OFFLINE</span>',
        }[sub_status]
        ts = status.last_update.astimezone(timezone.utc).strftime("%H:%M:%S UTC") if status.last_update else "—"
        st.markdown(
            f"""<div class="card" style="margin-bottom:0.7rem;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.3rem;">
                    <span class="card-title" style="margin:0;">{label}</span>{pill}
                  </div>
                  <div style="font-size:1.35rem;font-weight:800;color:var(--text);">{status.rows:,}
                    <span style="font-size:0.8rem;font-weight:500;color:var(--text-muted);">lignes</span>
                  </div>
                  <div class="card-sub">Màj : {ts} · {status.file_size_bytes/1024:.1f} KB</div>
                </div>
              </div>
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

    st.markdown(
        f"""<div class="hero">
          <div>
            <h1 class="hero-title">💹 Market Platform</h1>
            <div class="hero-subtitle">
              Plateforme cloud temps réel · Finnhub → Kafka → ML → Streamlit<br>
              <span style="color:var(--primary);font-weight:600;">AWS EC2 · S3 · SageMaker</span>
              &nbsp;·&nbsp; 5 symboles &nbsp;·&nbsp; 9 modèles ML &nbsp;·&nbsp; AutoML Optuna
            </div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.5rem;">
            {pill_html}
            <span style="color:var(--text-muted);font-size:0.78rem;">⏱ {ts_str}</span>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    if df.empty:
        df = data_module.load_quotes(data_module.RAW_DATA_PATH)
    _render_ticker(df)

    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        theme.kpi_card("Lignes traitées", f"{proc_status.rows:,}", sub=f"{proc_status.file_size_bytes/1024:.1f} KB · Consumer")
    with col2:
        theme.kpi_card("Lignes brutes", f"{raw_status.rows:,}", sub=f"{raw_status.file_size_bytes/1024:.1f} KB · Producer")
    with col3:
        theme.kpi_card("Symboles actifs", str(len(symbols)), sub=" · ".join(symbols) if symbols else "—")
    with col4:
        if last:
            delta_s = (data_module.now_utc() - last).total_seconds()
            age = f"{delta_s:.0f}s" if delta_s < 60 else f"{delta_s/60:.1f} min"
            theme.kpi_card("Dernière ingestion", f"il y a {age}", sub="Producer → Consumer")
        else:
            theme.kpi_card("Dernière ingestion", "—", sub="Pipeline non démarré")

    st.write("")
    theme.section_header("🏗️ Architecture cloud", "Flux de données bout en bout")
    _render_architecture()
    st.write("")

    left, right = st.columns([1.6, 1])
    with left:
        theme.section_header("🚀 Explorer le dashboard")
        _render_nav_cards()
    with right:
        theme.section_header("📡 État du pipeline")
        _render_pipeline(raw_status, proc_status)
        if not raw_status.exists and not proc_status.exists:
            theme.empty_state("🚀", "Pipeline non démarré",
                "Lance le producer et le consumer.", "`python -m producer.main`")

    time.sleep(5)
    st.rerun()


render()
