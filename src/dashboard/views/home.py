"""Home view — overview with status cards and quick links."""
from __future__ import annotations

from datetime import timezone

import streamlit as st

from dashboard import data as data_module
from dashboard import theme


def render() -> None:
    theme.inject_theme()

    raw_status = data_module.dataset_status(data_module.RAW_DATA_PATH)
    proc_status = data_module.dataset_status(data_module.PROCESSED_DATA_PATH)

    last = max(
        [s.last_update for s in (raw_status, proc_status) if s.last_update],
        default=None,
    )
    pipe_status = theme.freshness_status(last, idle_seconds=30, offline_seconds=180)

    theme.hero(
        title="💹 Market Platform",
        subtitle="Plateforme cloud temps réel — ingestion Kafka, analyse, signal directionnel.",
        status=pipe_status,
        last_update=last,
    )

    # ---- KPI row ----
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        theme.kpi_card(
            "Lignes brutes (producer)",
            f"{raw_status.rows:,}",
            sub=f"{raw_status.file_size_bytes / 1024:.1f} KB",
        )
    with col2:
        theme.kpi_card(
            "Lignes traitées (consumer)",
            f"{proc_status.rows:,}",
            sub=f"{proc_status.file_size_bytes / 1024:.1f} KB",
        )

    # Symbol count + last activity
    df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    if df.empty:
        df = data_module.load_quotes(data_module.RAW_DATA_PATH)

    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
    with col3:
        theme.kpi_card("Symboles actifs", str(len(symbols)),
                       sub=", ".join(symbols[:6]) + ("…" if len(symbols) > 6 else "") if symbols else "—")

    with col4:
        if last:
            delta_s = (data_module.now_utc() - last).total_seconds()
            sub = f"il y a {delta_s:.0f}s" if delta_s < 120 else last.astimezone(timezone.utc).strftime("%H:%M:%S UTC")
        else:
            sub = "Pipeline non démarré"
        theme.kpi_card("Dernière ingestion", sub, sub="Producer + Consumer")

    st.write("")  # spacer

    # ---- Two-column block: navigation cards + pipeline status ----
    left, right = st.columns([1.4, 1])
    with left:
        theme.section_header("Naviguer", "Choisis une vue dans le menu de gauche. Nouveau ici ? Va voir le 📚 Guide.")
        cards = [
            ("📈", "Marché", "Prix en temps réel, chandeliers, KPIs par symbole."),
            ("🔬", "Analyse", "Variations, distributions, leaderboard up/down."),
            ("⚙️", "Pipeline", "Flux de données Finnhub→Kafka→Consumer + latences."),
            ("🎯", "Recommandations", "Algo personnalisé qui apprend ton profil de risque."),
            ("🤖", "Signal IA", "Modèle directionnel + backtest + scoring live."),
            ("📚", "Guide", "Comment utiliser chaque section du dashboard."),
        ]
        # 3x2 grid via columns
        a, b = st.columns(2)
        for i, (emoji, title, desc) in enumerate(cards):
            target = a if i % 2 == 0 else b
            with target:
                st.markdown(
                    f"""
                    <div class="card">
                      <div style="font-size:1.6rem;">{emoji}</div>
                      <div class="card-value" style="font-size:1.15rem; margin-top:0.2rem;">{title}</div>
                      <div class="card-sub">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right:
        theme.section_header("État du pipeline")
        status_rows = [
            ("Producer (CSV brut)", raw_status),
            ("Consumer (CSV traité)", proc_status),
        ]
        for label, status in status_rows:
            sub_status = theme.freshness_status(status.last_update)
            label_pill = {
                "live": '<span class="pill pill-live"><span class="pill-dot"></span>LIVE</span>',
                "idle": '<span class="pill pill-idle"><span class="pill-dot"></span>IDLE</span>',
                "offline": '<span class="pill pill-offline"><span class="pill-dot"></span>OFFLINE</span>',
            }[sub_status]
            ts = status.last_update.astimezone(timezone.utc).strftime("%H:%M:%S UTC") if status.last_update else "—"
            st.markdown(
                f"""
                <div class="card" style="margin-bottom:0.7rem;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <div class="card-title">{label}</div>
                      <div style="margin-top:0.3rem;color:var(--text);">{status.rows:,} lignes</div>
                      <div class="card-sub">Dernière màj : {ts}</div>
                    </div>
                    <div>{label_pill}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not raw_status.exists and not proc_status.exists:
            theme.empty_state(
                "🚀",
                "Pipeline pas encore démarré",
                "Lance le producer puis le consumer pour voir les données arriver ici.",
                action="`PYTHONPATH=src python -m producer.main`",
            )


render()
