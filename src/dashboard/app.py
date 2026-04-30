
# --- Nouvelle structure multi-pages ---
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="💹 Market Platform", page_icon="💹", layout="wide")

RAW_DATA_PATH = Path("data/quotes_backup.csv")
PROCESSED_DATA_PATH = Path("data/processed_quotes.csv")

def load_data(path: str) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(file_path)
    if df.empty:
        return df
    df = df.copy()
    numeric_cols = [
        "price_current", "price_high", "price_low", "price_open",
        "price_previous_close", "delta_abs", "delta_pct", "volume"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    date_cols = ["ingested_at", "processed_at", "finnhub_timestamp"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    return df.sort_values("ingested_at") if "ingested_at" in df.columns else df

# --- Navigation ---
st.sidebar.image("https://img.icons8.com/fluency/96/stock-market.png", width=80)
st.sidebar.title("Market Platform")
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Accueil", "📈 Dashboard Marché", "🤖 Analyse ML", "ℹ️ À propos"],
    index=0
)

if page == "🏠 Accueil":
    st.title("💹 Market Platform - Accueil")
    st.markdown("""
    <h2>Bienvenue sur la plateforme cloud de données financières temps réel !</h2>
    <ul>
        <li>📊 <b>Dashboard Marché</b> : Visualisez les prix, volumes, variations et chandeliers en temps réel.</li>
        <li>🤖 <b>Analyse ML</b> : Prédisez la tendance du marché avec un modèle de Machine Learning intégré.</li>
        <li>🔗 <b>Intégration Cloud</b> : Pipeline Kafka, Docker, Finnhub, CSV, tout automatisé.</li>
    </ul>
    <br>
    <b>Utilisez le menu à gauche pour naviguer.</b>
    <br><br>
    <i>Projet cloud, moderne, évolutif.</i>
    """, unsafe_allow_html=True)
    st.image("https://images.unsplash.com/photo-1519125323398-675f0ddb6308?auto=format&fit=crop&w=800&q=80", use_column_width=True)

elif page == "📈 Dashboard Marché":
    st.title("📈 Dashboard Marché - Version Pro")
    st.caption("Sources live : CSV brut (producer) + CSV traité (consumer)")
    st.sidebar.header("⚙️ Options")
    refresh_seconds = st.sidebar.slider("⏱️ Auto-refresh (secondes)", min_value=2, max_value=30, value=5)
    if st.sidebar.button("🔄 Rafraîchir maintenant"):
        st.experimental_rerun()
    st.markdown(f"<meta http-equiv='refresh' content='{refresh_seconds}'>", unsafe_allow_html=True)
    source_mode = st.sidebar.selectbox(
        "Source principale",
        options=["processed", "raw", "both"],
        index=0,
    )
    raw_path = st.sidebar.text_input("Chemin CSV brut", value=str(RAW_DATA_PATH))
    processed_path = st.sidebar.text_input("Chemin CSV traité", value=str(PROCESSED_DATA_PATH))
    raw_df = load_data(raw_path)
    processed_df = load_data(processed_path)
    if source_mode == "processed":
        df = processed_df.copy()
    elif source_mode == "raw":
        df = raw_df.copy()
    else:
        df = pd.concat([processed_df, raw_df], ignore_index=True) if not (processed_df.empty and raw_df.empty) else pd.DataFrame()
    if df.empty:
        st.warning("Aucune donnée trouvée. Lance le producer et le consumer pour alimenter les CSV.")
        st.stop()
    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
    selected_symbols = st.sidebar.multiselect("📊 Symbols à afficher", options=symbols, default=symbols)
    rows_limit = st.sidebar.slider("Nombre de lignes affichées", min_value=20, max_value=1000, value=200, step=20)
    if selected_symbols and "symbol" in df.columns:
        filtered = df[df["symbol"].isin(selected_symbols)].copy()
    else:
        filtered = df.copy()
    filtered = filtered.tail(rows_limit)
    # Indicateurs clés
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lignes (filtrées)", f"{len(filtered):,}")
    c2.metric("Symbols actifs", f"{filtered['symbol'].nunique() if 'symbol' in filtered.columns else 0}")
    if "ingested_at" in filtered.columns:
        ingested_series = pd.to_datetime(filtered["ingested_at"], errors="coerce", utc=True).dropna()
        last_ingested = ingested_series.max() if not ingested_series.empty else None
    else:
        last_ingested = None
    c3.metric("Dernière ingestion", str(last_ingested) if pd.notna(last_ingested) else "N/A")
    c4.metric("Source", source_mode)
    tab_market, tab_indicators, tab_tables = st.tabs(["Marché", "Indicateurs", "Tables"])
    with tab_market:
        st.subheader("Prix courant dans le temps")
        if {"ingested_at", "symbol", "price_current"}.issubset(filtered.columns):
            chart_df = filtered[["ingested_at", "symbol", "price_current"]].dropna()
            if chart_df.empty:
                st.info("Pas assez de données pour tracer la courbe.")
            else:
                fig_price = px.line(
                    chart_df,
                    x="ingested_at",
                    y="price_current",
                    color="symbol",
                    title="Évolution du prix courant"
                )
                fig_price.update_layout(legend_title_text="Symbol")
                st.plotly_chart(fig_price, use_container_width=True)
        else:
            st.info("Colonnes nécessaires absentes pour tracer le graphique.")
        # Graphique chandeliers si données disponibles
        if {"ingested_at", "symbol", "price_open", "price_high", "price_low", "price_current"}.issubset(filtered.columns):
            for sym in selected_symbols:
                df_sym = filtered[filtered["symbol"] == sym]
                if not df_sym.empty:
                    fig_candle = go.Figure(data=[go.Candlestick(
                        x=df_sym["ingested_at"],
                        open=df_sym["price_open"],
                        high=df_sym["price_high"],
                        low=df_sym["price_low"],
                        close=df_sym["price_current"],
                        name=sym
                    )])
                    fig_candle.update_layout(title=f"Chandeliers {sym}")
                    st.plotly_chart(fig_candle, use_container_width=True)
    with tab_indicators:
        st.subheader("Variations (%) par symbole")
        if {"symbol", "delta_pct"}.issubset(filtered.columns):
            indicator_df = (
                filtered.dropna(subset=["symbol", "delta_pct"])
                .groupby("symbol", as_index=False)
                .agg(avg_delta_pct=("delta_pct", "mean"), last_delta_pct=("delta_pct", "last"))
                .sort_values("last_delta_pct", ascending=False)
            )
            st.dataframe(indicator_df, use_container_width=True)
        else:
            st.info("Les indicateurs ne sont disponibles que dans les données traitées du consumer.")
        if "direction" in filtered.columns:
            st.subheader("Répartition des directions")
            dir_counts = filtered["direction"].fillna("unknown").value_counts()
            dir_df = dir_counts.rename("count").reset_index().rename(columns={"index": "direction"})
            if dir_df.empty:
                st.info("Aucune direction calculée pour le moment.")
            else:
                fig_dir = px.bar(dir_df, x="direction", y="count", title="Répartition des directions")
                st.plotly_chart(fig_dir, use_container_width=True)
                st.dataframe(dir_df, use_container_width=True)
    with tab_tables:
        st.subheader("Derniers ticks")
        show_cols = [
            "ingested_at", "processed_at", "symbol", "price_current", "price_open", "price_high", "price_low",
            "price_previous_close", "delta_abs", "delta_pct", "direction", "ingestion_mode", "source", "finnhub_timestamp", "volume"
        ]
        existing_cols = [col for col in show_cols if col in filtered.columns]
        sort_col = "processed_at" if "processed_at" in filtered.columns else "ingested_at"
        st.dataframe(filtered[existing_cols].sort_values(sort_col, ascending=False), use_container_width=True, height=460)

elif page == "🤖 Analyse ML":
    st.title("🤖 Analyse Machine Learning")
    st.info("Section à compléter : intégration du modèle ML, affichage des prédictions, upload de modèle, etc.")
    st.markdown("""
    <ul>
        <li>Affichage des prédictions de tendance (haussier/baissier)</li>
        <li>Courbes ROC, matrice de confusion, etc.</li>
        <li>Possibilité d'uploader un modèle ou de tester sur de nouvelles données</li>
    </ul>
    """, unsafe_allow_html=True)

elif page == "ℹ️ À propos":
    st.title("ℹ️ À propos")
    st.markdown("""
    <b>Market Platform</b> - Projet cloud temps réel.<br>
    <ul>
        <li>Développé avec Python, Streamlit, Kafka, Docker, Finnhub, scikit-learn.</li>
        <li>Pipeline temps réel, Machine Learning, Dashboard interactif.</li>
        <li>Déployable sur le cloud (AWS, GCP, Azure...)</li>
    </ul>
    <br>
    <i>Contact : issad.tinhinane@gmail.com</i>
    """, unsafe_allow_html=True)
    st.write("Crédits icônes : icons8.com, Unsplash")

# --- Footer ---
st.markdown("""
<hr style='margin-top:40px;margin-bottom:10px;'>
<center><small>© 2026 Market Platform - Projet Cloud FinTech</small></center>
""", unsafe_allow_html=True)