"""Analysis view — variations, distributions, leaderboard."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import data as data_module
from dashboard import theme


def _sidebar(symbols: list[str]) -> dict:
    st.sidebar.markdown("### 🔬 Périmètre d'analyse")
    selected = st.sidebar.multiselect("Symboles", options=symbols, default=symbols)
    window = st.sidebar.slider("Fenêtre (lignes)", 50, 5000, 1000, 50)
    return {"selected": selected, "window": window}


def _leaderboard(df: pd.DataFrame) -> None:
    if "delta_pct" not in df.columns or "symbol" not in df.columns:
        st.info("La colonne `delta_pct` n'est pas disponible dans la source.")
        return

    latest = data_module.latest_per_symbol(df)
    if latest.empty:
        return

    sorted_df = latest.sort_values("delta_pct", ascending=False).dropna(subset=["delta_pct"])
    top = sorted_df.head(5)
    bottom = sorted_df.tail(5).iloc[::-1]

    col_top, col_bot = st.columns(2)

    def _list(target_col, items: pd.DataFrame, label: str, accent: str) -> None:
        with target_col:
            theme.section_header(label)
            for _, row in items.iterrows():
                pct = row.get("delta_pct")
                price = row.get("price_current")
                color = theme.COLORS["up"] if accent == "up" else theme.COLORS["down"]
                st.markdown(
                    f"""
                    <div class="card" style="margin-bottom:0.6rem;">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                          <div style="font-weight:700;font-size:1.05rem;">{row.get("symbol", "?")}</div>
                          <div class="card-sub">Prix {theme.format_price(price)}</div>
                        </div>
                        <div style="color:{color};font-weight:700;font-size:1.2rem;">
                          {theme.format_pct(pct)}
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    _list(col_top, top, "🏆 Top hausses", "up")
    _list(col_bot, bottom, "📉 Top baisses", "down")


def _variation_distribution(df: pd.DataFrame) -> None:
    if "delta_pct" not in df.columns:
        st.info("Pas de variation calculée.")
        return
    sub = df.dropna(subset=["delta_pct"])
    if sub.empty:
        st.info("Aucune variation valide.")
        return
    fig = px.histogram(sub, x="delta_pct", nbins=40, color_discrete_sequence=[theme.COLORS["primary"]])
    fig.update_traces(marker_line_color=theme.COLORS["bg"], marker_line_width=1)
    fig.update_layout(**theme.plotly_layout(
        height=320,
        title=dict(text="Distribution des variations (%)", x=0.0, font=dict(size=15)),
        xaxis_title="Δ %", yaxis_title="Fréquence",
        bargap=0.04,
    ))
    st.plotly_chart(fig, use_container_width=True)


def _direction_pie(df: pd.DataFrame) -> None:
    if "direction" not in df.columns:
        st.info("Colonne `direction` indisponible.")
        return
    counts = df["direction"].fillna("unknown").value_counts().reset_index()
    counts.columns = ["direction", "count"]
    color_map = {
        "up": theme.COLORS["up"],
        "down": theme.COLORS["down"],
        "flat": theme.COLORS["text_muted"],
        "unknown": "#475569",
    }
    fig = px.pie(counts, names="direction", values="count", hole=0.55,
                 color="direction", color_discrete_map=color_map)
    fig.update_traces(textinfo="label+percent", textposition="outside")
    fig.update_layout(**theme.plotly_layout(
        height=320,
        title=dict(text="Répartition des directions", x=0.0, font=dict(size=15)),
        showlegend=False,
    ))
    st.plotly_chart(fig, use_container_width=True)


def _avg_per_symbol(df: pd.DataFrame) -> None:
    if not {"symbol", "delta_pct"}.issubset(df.columns):
        return
    grouped = (df.dropna(subset=["delta_pct"])
                 .groupby("symbol", as_index=False)
                 .agg(avg=("delta_pct", "mean"),
                      latest=("delta_pct", "last"),
                      count=("delta_pct", "count"))
                 .sort_values("latest", ascending=False))
    fig = px.bar(grouped, x="symbol", y="latest",
                 color="latest",
                 color_continuous_scale=[theme.COLORS["down"], theme.COLORS["text_muted"], theme.COLORS["up"]],
                 color_continuous_midpoint=0)
    fig.update_layout(**theme.plotly_layout(
        height=340,
        title=dict(text="Variation actuelle par symbole", x=0.0, font=dict(size=15)),
        xaxis_title=None, yaxis_title="Δ %",
        coloraxis_showscale=False,
    ))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        grouped,
        use_container_width=True,
        column_config={
            "avg": st.column_config.NumberColumn("Δ moyen %", format="%.2f%%"),
            "latest": st.column_config.NumberColumn("Δ actuel %", format="%.2f%%"),
            "count": st.column_config.NumberColumn("# obs.", format="%d"),
        },
        hide_index=True,
    )


def render() -> None:
    theme.inject_theme()

    df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    last_ts = df["ingested_at"].dropna().max() if (not df.empty and "ingested_at" in df.columns) else None
    last_dt = last_ts.to_pydatetime() if last_ts is not None and pd.notna(last_ts) else None

    theme.hero(
        title="🔬 Analyse",
        subtitle="Variations, distributions, leaderboard hausse/baisse.",
        status=theme.freshness_status(last_dt),
        last_update=last_dt,
    )

    if df.empty:
        theme.empty_state("📊", "Pas encore de données traitées",
                          "Le consumer doit avoir tourné au moins quelques secondes pour alimenter `processed_quotes.csv`.")
        return

    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
    controls = _sidebar(symbols)
    df = data_module.filter_symbols(df, controls["selected"]).tail(controls["window"])

    theme.chip_row(controls["selected"]) if controls["selected"] else None

    # ---- Leaderboard ----
    theme.section_header("Leaderboard", "Snapshot du dernier tick par symbole.")
    _leaderboard(df)

    st.write("")

    # ---- Charts ----
    theme.section_header("Mouvements & directions")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        _variation_distribution(df)
    with c2:
        _direction_pie(df)

    st.write("")
    theme.section_header("Performance par symbole")
    _avg_per_symbol(df)


render()
