"""Signal IA — page orientée client.

Vue simple et actionnable : pour chaque actif, l'IA indique une tendance
(Haussier / Neutre / Baissier) et un niveau de confiance, sans aucun jargon
technique. Tout le détail modèle (performances, comparaisons, backtest) est
regroupé dans un volet « coulisses » optionnel, replié par défaut.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import data as data_module
from dashboard import theme

# Ensure src/ is importable so `from ml import ...` works.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


MODEL_PATH   = Path("data/models/direction_model.joblib")
REPORT_PATH  = Path("data/models/training_report.json")
AUTOML_PATH  = Path("data/models/automl_report.json")
HISTORY_DIR  = Path("data/history")


# ---------------------------------------------------------------------------
# Signal client (basé sur l'historique quotidien — toujours disponible)
# ---------------------------------------------------------------------------
def _history_symbols() -> list[str]:
    return sorted(
        sym for p in HISTORY_DIR.glob("*_1d.parquet")
        if (sym := p.stem.replace("_1d", "")) != "TEST"
    )


@st.cache_data(ttl=600, show_spinner=False)
def _signal_series(symbol: str) -> pd.DataFrame:
    """Renvoie la série de probabilités de hausse pour un actif, ou vide."""
    from ml import predict as ml_predict

    path = HISTORY_DIR / f"{symbol}_1d.parquet"
    if not path.exists():
        return pd.DataFrame()
    hist = pd.read_parquet(path)
    try:
        return ml_predict.predict_from_history(hist)
    except Exception:
        return pd.DataFrame()


def _verdict(proba: float) -> tuple[str, str, str, str]:
    """(label, flèche, couleur, phrase) en langage client."""
    if proba >= 0.53:
        return ("Haussier", "▲", theme.COLORS["up"],
                "L'IA penche vers une hausse à court terme.")
    if proba <= 0.47:
        return ("Baissier", "▼", theme.COLORS["down"],
                "L'IA penche vers une baisse à court terme.")
    return ("Neutre", "•", theme.COLORS["warn"],
            "Pas de tendance nette : mieux vaut rester prudent.")


def _confidence(proba: float, label: str) -> float:
    if label == "Haussier":
        return proba
    if label == "Baissier":
        return 1 - proba
    return max(proba, 1 - proba)


# ---------------------------------------------------------------------------
# Vue d'ensemble (watchlist de signaux)
# ---------------------------------------------------------------------------
def _overview(symbols: list[str]) -> None:
    cells = ""
    for sym in symbols:
        res = _signal_series(sym)
        if res.empty:
            badge = '<span class="badge badge-flat">— indisponible</span>'
            value, subtxt = "—", "Signal en préparation"
        else:
            proba = float(res["proba_up"].iloc[-1])
            label, arrow, color, _ = _verdict(proba)
            conf = _confidence(proba, label)
            badge = (f'<span class="badge" style="background:{color}22;color:{color};'
                     f'border:1px solid {color}55;">{arrow} {label}</span>')
            value, subtxt = f"{conf*100:.0f}%", "Confiance du signal"
        cells += (
            f'<div class="tile">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-size:1.15rem;font-weight:800;color:var(--text);">{sym}</span>{badge}</div>'
            f'<div class="tile-value" style="margin-top:0.4rem;">{value}</div>'
            f'<div class="tile-sub">{subtxt}</div></div>'
        )
    st.markdown(f'<div class="tile-grid cols-5">{cells}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Focus sur un actif
# ---------------------------------------------------------------------------
def _focus(symbol: str) -> None:
    res = _signal_series(symbol)
    if res.empty:
        theme.empty_state("⏳", "Signal en préparation",
                          f"Pas encore assez de données pour analyser {symbol}.")
        return

    proba = float(res["proba_up"].iloc[-1])
    label, arrow, color, phrase = _verdict(proba)
    conf = _confidence(proba, label)

    left, right = st.columns([1, 1.1], gap="large")

    with left:
        st.markdown(
            f"""
            <div class="card" style="border-top:3px solid {color};">
              <div class="card-title">Verdict de l'IA · {symbol}</div>
              <div style="display:flex;align-items:center;gap:0.6rem;margin:0.4rem 0;">
                <span style="font-size:2rem;font-weight:900;color:{color};letter-spacing:-0.02em;">
                  {arrow} {label}
                </span>
              </div>
              <div style="font-size:1rem;color:var(--text);margin-bottom:0.6rem;">{phrase}</div>
              <div class="card-sub">Niveau de confiance</div>
              <div style="background:var(--surface-alt);border-radius:999px;height:12px;
                          overflow:hidden;margin-top:0.35rem;border:1px solid var(--border);">
                <div style="width:{conf*100:.0f}%;height:100%;border-radius:999px;
                            background:linear-gradient(90deg,{color}aa,{color});"></div>
              </div>
              <div style="font-size:1.4rem;font-weight:800;color:var(--text);margin-top:0.5rem;">
                {conf*100:.0f}%
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("ℹ️ Indication informative fournie par un modèle d'IA — ne constitue pas un conseil en investissement.")

    with right:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=proba * 100,
            number={"suffix": "%", "font": {"size": 34, "color": theme.COLORS["text"]}},
            title={"text": "Probabilité de hausse", "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": theme.COLORS["text_muted"]},
                "bar": {"color": color},
                "bgcolor": theme.COLORS["surface_alt"],
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 47], "color": theme.COLORS["down_soft"]},
                    {"range": [47, 53], "color": theme.COLORS["warn_soft"]},
                    {"range": [53, 100], "color": theme.COLORS["up_soft"]},
                ],
            },
        ))
        gauge.update_layout(**theme.plotly_layout(height=240, margin=dict(l=20, r=20, t=50, b=10)))
        st.plotly_chart(gauge, use_container_width=True)

    # Évolution de la confiance dans le temps (langage simple)
    trend = res.tail(90).reset_index()
    x_col = trend.columns[0]
    trend["conf_haussiere"] = trend["proba_up"] * 100
    fig = px.area(trend, x=x_col, y="conf_haussiere",
                  color_discrete_sequence=[theme.COLORS["primary"]])
    fig.update_traces(line=dict(width=2), fillcolor="rgba(139,92,246,0.12)")
    fig.add_hline(y=50, line_dash="dash", line_color=theme.COLORS["text_muted"],
                  annotation_text="Neutre", annotation_position="top right")
    fig.update_layout(**theme.plotly_layout(
        height=300,
        title=dict(text=f"Évolution du signal haussier — {symbol}", x=0.0, font=dict(size=15)),
        xaxis_title=None, yaxis_title="Confiance hausse (%)",
        yaxis=dict(range=[0, 100]),
    ))
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Volet technique (optionnel, replié) — inchangé sur le fond
# ---------------------------------------------------------------------------
def _humanize_age(seconds: float) -> str:
    if seconds < 3600:
        return f"il y a {seconds/60:.0f} min"
    if seconds < 86400:
        return f"il y a {seconds/3600:.1f} h"
    return f"il y a {seconds/86400:.0f} j"


def _technical_details() -> None:
    if not REPORT_PATH.exists():
        st.info("Pas de rapport d'entraînement disponible.")
        return
    report = json.loads(REPORT_PATH.read_text())
    best = report.get("best_model", "?")
    summary = report.get("summary", {})
    base_rate = report.get("base_rate", float("nan"))
    n_rows = report.get("n_rows", 0)

    stat = MODEL_PATH.stat()
    age = (datetime.now(timezone.utc)
           - datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)).total_seconds()
    st.caption(f"Modèle `{best}` · {stat.st_size/1024:.0f} KB · entraîné {_humanize_age(age)} "
               f"· {n_rows:,} lignes · base rate {base_rate:.3f}")

    if summary:
        MODEL_LABELS = {
            "logreg": "Logistic Regression", "gbdt": "Gradient Boosting",
            "rf": "Random Forest", "mlp": "MLP Neural Net", "ada": "AdaBoost",
            "et": "Extra Trees", "xgb": "XGBoost", "lgbm": "LightGBM", "voting": "Voting Ensemble",
        }
        rows = [{"label": MODEL_LABELS.get(n, n.upper()),
                 "auc": s.get("roc_auc_mean", 0), "best": n == best}
                for n, s in summary.items()]
        df_m = pd.DataFrame(rows).sort_values("auc")
        colors = [theme.COLORS["up"] if b else theme.COLORS["primary"] for b in df_m["best"]]
        fig = go.Figure(go.Bar(
            y=df_m["label"], x=df_m["auc"], orientation="h",
            marker_color=colors, marker_line_width=0,
            text=[f"{v:.3f}" for v in df_m["auc"]], textposition="outside",
            textfont=dict(size=12, color="#3B3560"),
        ))
        fig.add_vline(x=0.5, line_dash="dot", line_color=theme.COLORS["warn"])
        fig.update_layout(**theme.plotly_layout(
            height=max(240, len(df_m) * 40),
            title=dict(text="Comparaison des modèles (ROC AUC)", x=0.0, font=dict(size=13)),
            xaxis=dict(range=[0.48, max(df_m["auc"]) + 0.01]), yaxis_title=None,
            showlegend=False, margin=dict(l=10, r=60, t=40, b=10),
        ))
        st.plotly_chart(fig, use_container_width=True)

    if AUTOML_PATH.exists():
        automl = json.loads(AUTOML_PATH.read_text())
        st.caption(f"AutoML (Optuna) : meilleur = {automl.get('best_model', '?')} "
                   f"· AUC {automl.get('best_auc', 0):.3f} · {automl.get('n_trials', 0)} essais.")


def _backtest_block() -> None:
    from ml.backtest import backtest_symbol

    st.markdown("**Backtest historique** — simulation sur données passées (holdout temporel strict).")
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
    symbol = c1.text_input("Symbole", value="AAPL").strip().upper()
    period = c2.selectbox("Période", ["3y", "5y", "7y", "10y"], index=1)
    train_years = c3.slider("Années entraînement", 1, 8, 5)
    threshold = c4.slider("Seuil long", 0.50, 0.70, 0.55, 0.01)
    if not st.button("▶️ Lancer le backtest", type="primary"):
        return
    try:
        with st.spinner(f"Backtest {symbol}…"):
            bt, summary = backtest_symbol(symbol, period, "1d", threshold, 2.0,
                                          train_years=float(train_years), horizon=5,
                                          threshold_bps_label=25.0)
    except Exception as exc:
        st.error(f"Backtest échoué : {exc}")
        return
    m1, m2, m3 = st.columns(3)
    with m1:
        theme.kpi_card("Stratégie", f"{summary['total_return_strategy']*100:.1f}%",
                       sub=f"Buy & Hold {summary['total_return_bh']*100:.1f}%")
    with m2:
        theme.kpi_card("Sharpe", f"{summary['sharpe_strategy']:.2f}",
                       sub=f"B&H {summary['sharpe_bh']:.2f}")
    with m3:
        theme.kpi_card("Max drawdown", f"{summary['max_drawdown_strategy']*100:.1f}%",
                       sub=f"{summary['n_trades']} trades")
    eq = bt[["equity_strat", "equity_bh"]].reset_index()
    xc = eq.columns[0]
    eq = eq.rename(columns={"equity_strat": "Stratégie", "equity_bh": "Buy & Hold"})
    long_df = eq.melt(id_vars=xc, value_vars=["Stratégie", "Buy & Hold"],
                      var_name="série", value_name="équity")
    fig = px.line(long_df, x=xc, y="équity", color="série",
                  color_discrete_map={"Stratégie": theme.COLORS["primary"],
                                      "Buy & Hold": theme.COLORS["text_muted"]})
    fig.update_layout(**theme.plotly_layout(height=340, xaxis_title=None,
                      yaxis_title="Équity (base 1.0)", legend=dict(orientation="h", y=-0.2)))
    st.plotly_chart(fig, use_container_width=True)


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
        subtitle="Notre intelligence artificielle analyse le marché pour vous — un signal clair, sans jargon.",
        status="live" if ml_predict.model_available() else "offline",
        last_update=last_train,
    )

    if not ml_predict.model_available():
        theme.empty_state("🤖", "Signal indisponible",
                          "Le moteur d'analyse se prépare. Reviens dans un instant.")
        return

    symbols = _history_symbols()
    if not symbols:
        theme.empty_state("📡", "Aucun actif à analyser",
                          "Les données de marché ne sont pas encore disponibles.")
        return

    # 1. Vue d'ensemble
    theme.section_header("📡 Vos signaux du jour",
                         "Tendance estimée par l'IA pour chaque actif suivi")
    _overview(symbols)

    # 2. Focus sur un actif
    st.write("")
    theme.section_header("🔎 Analyser un actif en détail")
    sym = st.selectbox("Choisis un actif", symbols, label_visibility="collapsed")
    _focus(sym)

    # 3. Volet technique (optionnel)
    st.write("")
    with st.expander("🔧 Coulisses techniques (optionnel — pour les curieux)", expanded=False):
        st.caption("Ces éléments s'adressent à un public technique. Un client n'en a pas besoin.")
        _technical_details()
        st.divider()
        _backtest_block()


render()
