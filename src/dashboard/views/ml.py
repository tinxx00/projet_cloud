"""ML view — model card, training report, backtest, live prediction.

UI layer only. La logique métier reste dans `src/ml/*` et n'est pas
touchée ici. Trois sections :
  1. **Model Card** : ce qui est chargé en mémoire.
  2. **Performance** : rapport d'entraînement (walk-forward CV).
  3. **Backtest** : holdout out-of-sample interactif.
  4. **Prédiction live** : scoring auto-rafraîchi sur les données consumer.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import data as data_module
from dashboard import theme

# Ensure src/ is importable so `from ml import ...` works.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


MODEL_PATH = Path("data/models/direction_model.joblib")
REPORT_PATH = Path("data/models/training_report.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _humanize_age(seconds: float) -> str:
    if seconds < 60:
        return f"il y a {seconds:.0f}s"
    if seconds < 3600:
        return f"il y a {seconds/60:.0f} min"
    if seconds < 86400:
        return f"il y a {seconds/3600:.1f} h"
    return f"il y a {seconds/86400:.0f} j"


def _no_model_state() -> None:
    theme.empty_state(
        "🤖",
        "Aucun modèle entraîné",
        "Le fichier `data/models/direction_model.joblib` n'existe pas. "
        "Entraîne d'abord le modèle puis reviens ici — toute la page se peuplera automatiquement.",
        action="`PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN`",
    )


# ---------------------------------------------------------------------------
# Model Card
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_bundle(_signature: tuple[float, int]) -> dict:
    """Charge le bundle modèle (joblib). Cache invalidé sur mtime+size."""
    return joblib.load(MODEL_PATH)


def _model_card() -> dict:
    """Affiche la carte d'identité du modèle et renvoie le bundle chargé."""
    stat = MODEL_PATH.stat()
    bundle = _load_bundle((stat.st_mtime, stat.st_size))

    config = bundle.get("config", {})
    best = bundle.get("best_name", "?")
    feat_cols = bundle.get("feature_columns", [])
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    age = (datetime.now(timezone.utc) - mtime).total_seconds()

    symbols = config.get("symbols", []) or []
    horizon = config.get("horizon", "?")
    threshold_bps = config.get("threshold_bps", "?")
    period = config.get("period", "?")
    interval = config.get("interval", "?")

    syms_html = "".join(
        f'<span class="badge badge-flat" style="margin:0 0.25rem 0.25rem 0;">{s}</span>'
        for s in symbols
    ) or "—"

    st.markdown(
        f"""
        <div class="card" style="background:linear-gradient(135deg, var(--surface) 0%, rgba(34,211,238,0.08) 100%);">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">
            <div style="flex:1 1 320px;">
              <div class="card-title">📦 Model Card</div>
              <div style="display:flex;align-items:center;gap:0.7rem;margin-top:0.3rem;">
                <span style="font-size:1.7rem;font-weight:800;letter-spacing:-0.02em;color:var(--text);">
                  {best.upper()}
                </span>
                <span class="pill pill-live"><span class="pill-dot"></span>MODÈLE CHARGÉ</span>
              </div>
              <div class="card-sub" style="margin-top:0.4rem;font-family:ui-monospace,Menlo,monospace;">
                {MODEL_PATH} · {stat.st_size/1024:.1f} KB · entraîné {_humanize_age(age)}
              </div>
              <div style="margin-top:0.85rem;font-size:0.88rem;color:var(--text-muted);">
                <b style="color:var(--text);">Horizon</b> {horizon}j ·
                <b style="color:var(--text);">Seuil label</b> {threshold_bps} bps ·
                <b style="color:var(--text);">Période</b> {period} ·
                <b style="color:var(--text);">Fréq.</b> {interval}
              </div>
              <div style="margin-top:0.7rem;">
                <span class="card-title" style="margin-right:0.4rem;">Univers</span>
                {syms_html}
              </div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.4rem;min-width:160px;">
              <div class="card-title">Features</div>
              <div style="font-size:1.6rem;font-weight:700;color:var(--primary);">{len(feat_cols)}</div>
              <div class="card-sub">indicateurs techniques</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"🔧 Détails techniques · {len(feat_cols)} features"):
        cols = st.columns(4)
        for i, fc in enumerate(feat_cols):
            cols[i % 4].markdown(f"`{fc}`")

    return bundle


# ---------------------------------------------------------------------------
# Training summary
# ---------------------------------------------------------------------------
def _training_summary() -> None:
    if not REPORT_PATH.exists():
        st.info("Pas de rapport d'entraînement (`training_report.json`).")
        return
    report = json.loads(REPORT_PATH.read_text())
    best = report.get("best_model", "?")
    summary = report.get("summary", {}).get(best, {})

    c1, c2, c3, c4 = st.columns(4)
    with c1: theme.kpi_card("Modèle retenu", best.upper(), sub="Sélection par AUC")
    with c2: theme.kpi_card("ROC AUC",
                            f"{summary.get('roc_auc_mean', float('nan')):.3f}",
                            sub=f"σ ±{summary.get('roc_auc_std', 0):.3f}")
    with c3: theme.kpi_card("Accuracy",
                            f"{summary.get('accuracy_mean', float('nan')):.3f}",
                            sub=f"σ ±{summary.get('accuracy_std', 0):.3f}")
    with c4: theme.kpi_card("F1 score",
                            f"{summary.get('f1_mean', float('nan')):.3f}",
                            sub=f"σ ±{summary.get('f1_std', 0):.3f}")

    with st.expander("📋 Configuration & taux de base"):
        st.json({"config": report.get("config"),
                 "base_rate": report.get("base_rate"),
                 "n_rows": report.get("n_rows")})


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
def _backtest_block() -> None:
    from ml.backtest import backtest_symbol

    theme.section_header(
        "🧪 Backtest historique",
        "Holdout temporel strict — entraînement sur les premières années, test sur la suite.",
    )

    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
    symbol = c1.text_input("Symbole", value="AAPL").strip().upper()
    period = c2.selectbox("Période", ["3y", "5y", "7y", "10y", "15y"], index=3)
    train_years = c3.slider("Années entraînement", 1, 10, 5)
    threshold = c4.slider("Seuil long", 0.50, 0.70, 0.55, 0.01)

    cost_col, horizon_col, label_col, run_col = st.columns([1, 1, 1, 1])
    cost = cost_col.number_input("Coût (bps)", value=2.0, min_value=0.0, max_value=20.0, step=0.5)
    horizon = horizon_col.slider("Horizon (jours)", 1, 10, 5)
    label_bps = label_col.number_input("Seuil label (bps)", value=25.0, min_value=0.0, step=5.0)
    run_col.write("")
    run_col.write("")
    run = run_col.button("▶️ Lancer", use_container_width=True, type="primary")

    if not run:
        st.caption("Configure les paramètres ci-dessus puis clique sur **Lancer** pour exécuter le backtest.")
        return

    try:
        with st.spinner(f"Backtest sur {symbol} en cours…"):
            bt, summary = backtest_symbol(
                symbol, period, "1d", threshold, cost,
                train_years=float(train_years), horizon=horizon,
                threshold_bps_label=label_bps,
            )
    except Exception as exc:
        st.error(f"❌ Backtest échoué : {exc}")
        return

    m1, m2, m3, m4 = st.columns(4)
    strat = summary["total_return_strategy"] * 100
    bh = summary["total_return_bh"] * 100
    delta_vs_bh = strat - bh
    with m1:
        theme.kpi_card("Stratégie cumulée", f"{strat:.2f}%",
                       delta=delta_vs_bh, delta_format="vs B&H {:+.2f}%")
    with m2:
        theme.kpi_card("Sharpe ratio", f"{summary['sharpe_strategy']:.2f}",
                       sub=f"B&H {summary['sharpe_bh']:.2f}")
    with m3:
        theme.kpi_card("Max drawdown", f"{summary['max_drawdown_strategy']*100:.1f}%",
                       sub=f"B&H {summary['max_drawdown_bh']*100:.1f}%")
    with m4:
        theme.kpi_card("Hit rate · trades",
                       f"{summary['hit_rate']*100:.1f}%",
                       sub=f"{summary['n_trades']} trades · expo {summary['exposure']*100:.0f}%")

    st.write("")

    eq_df = bt[["equity_strat", "equity_bh"]].reset_index()
    x_col = eq_df.columns[0]
    eq_df = eq_df.rename(columns={"equity_strat": "Stratégie", "equity_bh": "Buy & Hold"})
    long_df = eq_df.melt(id_vars=x_col, value_vars=["Stratégie", "Buy & Hold"],
                         var_name="série", value_name="équity")
    fig_eq = px.line(long_df, x=x_col, y="équity", color="série",
                     color_discrete_map={"Stratégie": theme.COLORS["primary"],
                                         "Buy & Hold": theme.COLORS["text_muted"]})
    fig_eq.update_traces(line=dict(width=2.2))
    fig_eq.update_layout(**theme.plotly_layout(
        height=380,
        title=dict(text=f"Équity curve {summary['symbol']} (test {summary['test_start']} → {summary['test_end']})",
                   x=0.0, font=dict(size=15)),
        xaxis_title=None, yaxis_title="Équity (base 1.0)",
        legend=dict(orientation="h", y=-0.2),
    ))
    st.plotly_chart(fig_eq, use_container_width=True)

    fig_p = px.line(bt.reset_index(), x=bt.index.name or x_col, y="proba_up",
                    color_discrete_sequence=[theme.COLORS["warn"]])
    fig_p.add_hline(y=threshold, line_dash="dash", line_color=theme.COLORS["primary"],
                    annotation_text=f"seuil {threshold:.2f}", annotation_position="top right")
    fig_p.update_layout(**theme.plotly_layout(
        height=260,
        title=dict(text="Probabilité modèle (out-of-sample)", x=0.0, font=dict(size=14)),
        xaxis_title=None, yaxis_title="P(haussier)",
    ))
    st.plotly_chart(fig_p, use_container_width=True)

    with st.expander("📜 Aperçu des dernières lignes"):
        st.dataframe(
            bt[["Close", "proba_up", "signal", "fwd_ret", "strategy_ret",
                "equity_strat", "equity_bh"]].tail(60),
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Live prediction (auto-refreshable)
# ---------------------------------------------------------------------------
def _live_prediction(sym: str, freq: str) -> None:
    """Affiche le scoring live pour un symbole / une fréquence donnés."""
    from ml import predict as ml_predict

    df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    last_ts = (df["ingested_at"].dropna().max()
               if (not df.empty and "ingested_at" in df.columns) else None)
    last_dt = last_ts.to_pydatetime() if last_ts is not None and pd.notna(last_ts) else None
    fresh = theme.freshness_status(last_dt)

    pill = {
        "live": '<span class="pill pill-live"><span class="pill-dot"></span>STREAM LIVE</span>',
        "idle": '<span class="pill pill-idle"><span class="pill-dot"></span>STREAM IDLE</span>',
        "offline": '<span class="pill pill-offline"><span class="pill-dot"></span>STREAM OFFLINE</span>',
    }[fresh]
    refresh_ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    margin-bottom:0.7rem;">
          <div style="color:var(--text-muted);font-size:0.88rem;">
            Symbole <b style="color:var(--text);">{sym}</b> · barres <b style="color:var(--text);">{freq}</b>
          </div>
          <div>{pill}
            <span style="color:var(--text-muted);font-size:0.78rem;margin-left:0.5rem;">
              ⏱ rafraîchi à {refresh_ts}
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df.empty:
        theme.empty_state("📡", "Pas de données consumer",
                          "Lance le pipeline pour scorer en live.")
        return

    preds = ml_predict.predict_from_processed_csv(df, sym, freq=freq)
    if preds.empty:
        theme.empty_state(
            "⏳", "Pas assez de barres pour scorer",
            f"Besoin d'au moins ~30 barres {freq} pour {sym}. "
            "Laisse tourner le pipeline plus longtemps.",
        )
        return

    last = preds.iloc[-1]
    proba = float(last["proba_up"])
    signal = "LONG" if last["signal"] == 1 else "FLAT"
    color = theme.COLORS["up"] if signal == "LONG" else theme.COLORS["text_muted"]

    c1, c2, c3 = st.columns(3)
    with c1:
        theme.kpi_card("Probabilité hausse", f"{proba*100:.1f}%",
                       delta=(proba - 0.5) * 100,
                       delta_format="vs neutre {:+.1f} pp")
    with c2:
        st.markdown(
            f"""
            <div class="card">
              <div class="card-title">Signal</div>
              <div class="card-value" style="color:{color};">{signal}</div>
              <div class="card-sub">Sur la dernière barre {freq}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        theme.kpi_card("Barres scorées", f"{len(preds):,}",
                       sub=f"Symbole {sym} · fréquence {freq}")

    fig = px.line(preds.reset_index(), x=preds.index.name or "index",
                  y="proba_up",
                  color_discrete_sequence=[theme.COLORS["primary"]])
    fig.add_hline(y=0.5, line_dash="dash", line_color=theme.COLORS["text_muted"])
    fig.update_traces(line=dict(width=2.2))
    fig.update_layout(**theme.plotly_layout(
        height=320,
        title=dict(text=f"Probabilité haussière (live) — {sym} {freq}",
                   x=0.0, font=dict(size=14)),
        xaxis_title=None, yaxis_title="P(haussier)",
    ))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📜 30 dernières barres scorées"):
        st.dataframe(
            preds.tail(30), use_container_width=True,
            column_config={
                "proba_up": st.column_config.ProgressColumn(
                    "P(haussier)", min_value=0, max_value=1, format="%.2f"),
                "signal": st.column_config.NumberColumn("Signal", format="%d"),
            },
        )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render() -> None:
    theme.inject_theme()
    from ml import predict as ml_predict

    last_train = (datetime.fromtimestamp(MODEL_PATH.stat().st_mtime, tz=timezone.utc)
                  if MODEL_PATH.exists() else None)

    theme.hero(
        title="🤖 Signal IA",
        subtitle="Modèle directionnel court terme · backtest holdout · scoring live sur le flux consumer.",
        status="live" if ml_predict.model_available() else "offline",
        last_update=last_train,
    )

    if not ml_predict.model_available():
        _no_model_state()
        return

    # 1. Model Card
    _model_card()

    # 2. Performance d'entraînement
    st.write("")
    theme.section_header("📊 Performance d'entraînement",
                         "Walk-forward CV sur l'historique d'entraînement.")
    _training_summary()

    # 3. Backtest interactif
    st.write("")
    _backtest_block()

    # 4. Prédiction live (auto-refreshable)
    st.write("")
    theme.section_header(
        "⚡ Prédiction live",
        "Le modèle agrège les ticks consumer en barres OHLC et score chaque nouvelle barre.",
    )

    df_proc = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    symbols = (sorted(df_proc["symbol"].dropna().unique().tolist())
               if (not df_proc.empty and "symbol" in df_proc.columns) else [])

    if not symbols:
        theme.empty_state(
            "📡", "Pas encore de données consumer",
            "Lance producer + consumer pour scorer en live. La page se mettra à jour automatiquement.",
        )
        return

    # Sidebar controls (live mode + interval)
    with st.sidebar:
        st.markdown("### ⚡ Mode live")
        live = st.toggle("Auto-refresh", value=True,
                         help="Rafraîchit la prédiction toutes les N secondes "
                              "sans recharger toute la page.")
        interval = st.select_slider("Intervalle (s)", options=[3, 5, 10, 15, 30],
                                    value=5, disabled=not live)

    c1, c2 = st.columns([1, 1])
    sym = c1.selectbox("Symbole", symbols)
    freq = c2.selectbox("Fréquence d'agrégation", ["1min", "5min", "15min"], index=1)

    if live:
        wrapped = st.fragment(run_every=f"{interval}s")(_live_prediction)
        wrapped(sym, freq)
    else:
        _live_prediction(sym, freq)


render()
