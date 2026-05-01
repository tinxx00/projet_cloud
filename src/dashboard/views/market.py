"""Market view — live prices, candles, KPIs per symbol."""
from __future__ import annotations

from datetime import timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import data as data_module
from dashboard import theme


def _sidebar_controls(symbols: list[str]) -> dict:
    st.sidebar.markdown("### ⚙️ Paramètres")
    refresh = st.sidebar.toggle("Rafraîchissement live", value=True,
                                help="Met à jour les graphiques sans recharger la page.")
    interval = st.sidebar.select_slider(
        "Intervalle (s)", options=[2, 3, 5, 10, 15, 30], value=5, disabled=not refresh,
    )

    st.sidebar.markdown("### 📊 Filtres")
    selected = st.sidebar.multiselect("Symboles", options=symbols, default=symbols)
    rows = st.sidebar.slider("Profondeur historique (lignes)", min_value=50, max_value=2000,
                             value=400, step=50)
    source = st.sidebar.radio(
        "Source", options=["processed", "raw", "both"], index=0, horizontal=True,
        help="`processed` = données enrichies par le consumer, `raw` = sortie producer brute.",
    )
    return {
        "refresh": refresh,
        "interval": interval,
        "selected": selected,
        "rows": rows,
        "source": source,
    }


def _load(source: str) -> pd.DataFrame:
    raw = data_module.load_quotes(data_module.RAW_DATA_PATH)
    proc = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    if source == "processed":
        return proc
    if source == "raw":
        return raw
    if proc.empty and raw.empty:
        return pd.DataFrame()
    return pd.concat([proc, raw], ignore_index=True)


def _kpi_row(latest: pd.DataFrame) -> None:
    if latest.empty:
        return
    cols = st.columns(min(len(latest), 6))
    for col, (_, row) in zip(cols, latest.head(6).iterrows()):
        with col:
            price = row.get("price_current")
            delta = row.get("delta_pct")
            direction = row.get("direction", "unknown")
            badge = theme.direction_badge(direction)
            sub = f"Prev close {theme.format_price(row.get('price_previous_close'))}"
            color_cls = "card-delta-up" if (delta or 0) > 0 else (
                "card-delta-down" if (delta or 0) < 0 else "card-delta-flat")
            arrow = "▲" if (delta or 0) > 0 else ("▼" if (delta or 0) < 0 else "•")
            delta_html = (
                f'<div class="{color_cls}" style="font-size:0.9rem;margin-top:0.25rem;">'
                f'{arrow} {theme.format_pct(delta)}</div>'
                if delta is not None and pd.notna(delta) else ""
            )
            st.markdown(
                f"""
                <div class="card">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div class="card-title">{row.get("symbol", "?")}</div>
                    {badge}
                  </div>
                  <div class="card-value">{theme.format_price(price)}</div>
                  {delta_html}
                  <div class="card-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _price_chart(df: pd.DataFrame, symbols: list[str]) -> None:
    if df.empty or not {"ingested_at", "symbol", "price_current"}.issubset(df.columns):
        theme.empty_state("📈", "Pas encore de données de prix",
                          "Démarre le producer + consumer pour alimenter les graphes.")
        return
    chart_df = df[df["symbol"].isin(symbols)][["ingested_at", "symbol", "price_current"]].dropna()
    if chart_df.empty:
        theme.empty_state("📉", "Pas de série exploitable",
                          "Aucune mesure de prix valide sur la fenêtre sélectionnée.")
        return
    fig = px.line(
        chart_df, x="ingested_at", y="price_current", color="symbol",
        line_shape="spline", render_mode="webgl",
    )
    fig.update_traces(line=dict(width=2))
    fig.update_layout(**theme.plotly_layout(
        height=420,
        title=dict(text="Évolution des prix (live)", x=0.0, font=dict(size=16)),
        legend=dict(orientation="h", y=-0.18, x=0.0),
        xaxis_title=None, yaxis_title="Prix",
    ))
    st.plotly_chart(fig, use_container_width=True)


def _candles(df: pd.DataFrame, symbols: list[str]) -> None:
    needed = {"ingested_at", "symbol", "price_open", "price_high", "price_low", "price_current"}
    if df.empty or not needed.issubset(df.columns):
        st.info("Données OHLC incomplètes — bascule sur la source `processed` ou attends plus de ticks.")
        return
    cols = st.columns(min(len(symbols), 2)) if symbols else [st]
    for i, sym in enumerate(symbols):
        sub = df[df["symbol"] == sym]
        if sub.empty:
            continue
        target = cols[i % len(cols)]
        with target:
            fig = go.Figure(data=[go.Candlestick(
                x=sub["ingested_at"],
                open=sub["price_open"],
                high=sub["price_high"],
                low=sub["price_low"],
                close=sub["price_current"],
                increasing_line_color=theme.COLORS["up"],
                decreasing_line_color=theme.COLORS["down"],
                showlegend=False,
            )])
            fig.update_layout(**theme.plotly_layout(
                height=300,
                title=dict(text=f"Chandeliers — {sym}", x=0.0, font=dict(size=14)),
                xaxis_rangeslider_visible=False,
                xaxis_title=None, yaxis_title=None,
            ))
            st.plotly_chart(fig, use_container_width=True)


def _ticks_table(df: pd.DataFrame) -> None:
    cols = [c for c in [
        "ingested_at", "symbol", "price_current", "delta_pct", "direction",
        "price_open", "price_high", "price_low", "price_previous_close",
        "ingestion_mode", "source",
    ] if c in df.columns]
    if not cols:
        return
    show = df[cols].sort_values(cols[0], ascending=False).head(150)
    st.dataframe(
        show,
        use_container_width=True,
        height=380,
        column_config={
            "ingested_at": st.column_config.DatetimeColumn("Ingéré à", format="HH:mm:ss UTC"),
            "symbol": st.column_config.TextColumn("Symbole", width="small"),
            "price_current": st.column_config.NumberColumn("Prix", format="%.2f"),
            "delta_pct": st.column_config.NumberColumn("Δ %", format="%.2f%%"),
            "direction": st.column_config.TextColumn("Dir.", width="small"),
        },
    )


def _live_block(controls: dict) -> None:
    """Live region: rerun-on-interval without reloading the whole page."""
    df = _load(controls["source"])
    if df.empty:
        theme.empty_state("📡", "En attente de ticks",
                          "Le pipeline tourne ? Vérifie le producer / consumer.")
        return

    df = data_module.filter_symbols(df, controls["selected"])
    df = df.tail(controls["rows"])

    last_ts = df["ingested_at"].dropna().max() if "ingested_at" in df.columns else None
    last_dt = last_ts.to_pydatetime() if last_ts is not None and pd.notna(last_ts) else None
    status = theme.freshness_status(last_dt)
    pill = {
        "live": '<span class="pill pill-live"><span class="pill-dot"></span>STREAM LIVE</span>',
        "idle": '<span class="pill pill-idle"><span class="pill-dot"></span>STREAM IDLE</span>',
        "offline": '<span class="pill pill-offline"><span class="pill-dot"></span>STREAM OFFLINE</span>',
    }[status]
    ts_text = last_dt.astimezone(timezone.utc).strftime("%H:%M:%S UTC") if last_dt else "—"
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">
          <div style="color:var(--text-muted);font-size:0.9rem;">
            Affichage de <b>{len(df):,}</b> lignes · {df['symbol'].nunique() if 'symbol' in df.columns else 0} symboles · source <b>{controls["source"]}</b>
          </div>
          <div>{pill} <span style="color:var(--text-muted);font-size:0.8rem;margin-left:0.4rem;">⏱ {ts_text}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    latest = data_module.latest_per_symbol(df)
    _kpi_row(latest)
    st.write("")

    tabs = st.tabs(["📈 Prix", "🕯 Chandeliers", "📜 Ticks"])
    with tabs[0]:
        _price_chart(df, controls["selected"])
    with tabs[1]:
        _candles(df, controls["selected"])
    with tabs[2]:
        _ticks_table(df)


def render() -> None:
    theme.inject_theme()

    # Bootstrap symbol options (fast pull, before any filter)
    bootstrap_df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    if bootstrap_df.empty:
        bootstrap_df = data_module.load_quotes(data_module.RAW_DATA_PATH)
    all_symbols = sorted(bootstrap_df["symbol"].dropna().unique().tolist()) \
        if "symbol" in bootstrap_df.columns else []

    controls = _sidebar_controls(all_symbols)

    last_ts = bootstrap_df["ingested_at"].dropna().max() if "ingested_at" in bootstrap_df.columns else None
    last_dt = last_ts.to_pydatetime() if last_ts is not None and pd.notna(last_ts) else None
    theme.hero(
        title="📈 Marché",
        subtitle="Prix, chandeliers, ticks — flux Kafka avec fallback CSV.",
        status=theme.freshness_status(last_dt),
        last_update=last_dt,
    )

    if not all_symbols:
        theme.empty_state("📡", "Aucun symbole détecté",
                          "Lance le pipeline puis reviens ici. Les CSV sont scrutés en permanence.")
        return

    if controls["refresh"]:
        # Re-run only this fragment every N seconds
        wrapped = st.fragment(run_every=f"{controls['interval']}s")(_live_block)
        wrapped(controls)
    else:
        _live_block(controls)


render()
