"""ML view — model report, backtest runner, live prediction.

UI layer only. The business logic lives in `src/ml/*` and is unchanged.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import data as data_module
from dashboard import theme

# Ensure src/ is importable so `from ml import ...` works.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _no_model_state() -> None:
    theme.empty_state(
        "🤖",
        "Aucun modèle entraîné",
        "Entraîne d'abord le modèle avec la commande ci-dessous, puis reviens ici.",
        action="`PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN`",
    )


def _training_summary(report_path: Path) -> None:
    if not report_path.exists():
        st.info("Pas de rapport d'entraînement (`training_report.json`).")
        return
    report = json.loads(report_path.read_text())
    best = report.get("best_model", "?")
    summary = report.get("summary", {}).get(best, {})

    c1, c2, c3, c4 = st.columns(4)
    with c1: theme.kpi_card("Modèle", best.upper(), sub="Sélection auto par AUC")
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


def _backtest_block() -> None:
    from ml.backtest import backtest_symbol

    theme.section_header("🧪 Backtest historique",
                        "Holdout temporel strict — entraînement sur les premières années, test sur la suite.")

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

    # KPIs
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

    # Equity curve
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

    # Probability chart
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


def _live_block() -> None:
    from ml import predict as ml_predict

    theme.section_header("⚡ Prédiction live",
                        "À partir des ticks consumer agrégés en barres OHLC.")

    df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    if df.empty:
        theme.empty_state("📡", "Pas encore de données consumer",
                          "Lance producer + consumer pour scorer en live.")
        return

    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
    if not symbols:
        theme.empty_state("🔍", "Aucun symbole disponible côté consumer",
                          "Vérifie que `processed_quotes.csv` contient bien une colonne `symbol`.")
        return

    c1, c2 = st.columns([1, 1])
    sym = c1.selectbox("Symbole", symbols)
    freq = c2.selectbox("Fréquence d'agrégation", ["1min", "5min", "15min"], index=1)

    preds = ml_predict.predict_from_processed_csv(df, sym, freq=freq)
    if preds.empty:
        theme.empty_state("⏳", "Pas assez de barres pour scorer",
                          f"Besoin d'au moins ~30 barres {freq} pour {sym}. "
                          "Laisse tourner le pipeline plus longtemps.")
        return

    last = preds.iloc[-1]
    proba = float(last["proba_up"])
    signal = "LONG" if last["signal"] == 1 else "FLAT"
    color = theme.COLORS["up"] if signal == "LONG" else theme.COLORS["text_muted"]

    c1, c2, c3 = st.columns(3)
    with c1: theme.kpi_card("Probabilité hausse", f"{proba*100:.1f}%",
                            delta=(proba - 0.5) * 100, delta_format="vs neutre {:+.1f}pp")
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
    with c3: theme.kpi_card("Barres scorées", f"{len(preds):,}",
                            sub=f"Symbole {sym} · fréquence {freq}")

    fig = px.line(preds.reset_index(), x=preds.index.name or "index", y="proba_up",
                  color_discrete_sequence=[theme.COLORS["primary"]])
    fig.add_hline(y=0.5, line_dash="dash", line_color=theme.COLORS["text_muted"])
    fig.update_layout(**theme.plotly_layout(
        height=300,
        title=dict(text=f"Probabilité modèle — {sym} ({freq})", x=0.0, font=dict(size=14)),
        xaxis_title=None, yaxis_title="P(haussier)",
    ))
    st.plotly_chart(fig, use_container_width=True)


def render() -> None:
    theme.inject_theme()
    from ml import predict as ml_predict

    theme.hero(
        title="🤖 Signal IA",
        subtitle="Modèle directionnel + backtest out-of-sample + scoring live.",
        status="live" if ml_predict.model_available() else "offline",
    )

    if not ml_predict.model_available():
        _no_model_state()
        return

    theme.section_header("📊 Performance d'entraînement", "Walk-forward CV.")
    _training_summary(Path("data/models/training_report.json"))

    st.write("")
    _backtest_block()

    st.write("")
    _live_block()


render()
