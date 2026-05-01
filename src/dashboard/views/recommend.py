"""Placement recommendation view with adaptive risk profile learning.

L'utilisateur démarre avec un profil initial (slider 0..1). Pour chaque
recommandation, il peut donner un feedback : "trop risqué", "OK" ou "pas
assez risqué". Le profil est mis à jour via une moyenne exponentielle
de la cible déduite du feedback. Toutes les notations sont persistées
dans ``data/user_feedback.csv`` pour réentraîner le profil entre sessions.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import data as data_module
from dashboard import feedback as fb_module
from dashboard import theme

# Ensure src/ is importable so `from ml import ...` works.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ml import risk as risk_module


DEFAULT_SYMBOLS = ("AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "NVDA", "META", "JPM", "KO", "XOM")


@st.cache_data(ttl=900, show_spinner=False)
def _cached_universe_metrics(symbols: tuple[str, ...]) -> pd.DataFrame:
    return risk_module.compute_universe_metrics(list(symbols))


def _profile_label(pref: float) -> tuple[str, str]:
    if pref < 0.34:
        return "🛡️ Prudent", theme.COLORS["up"]
    if pref < 0.67:
        return "⚖️ Équilibré", theme.COLORS["primary"]
    return "🚀 Audacieux", theme.COLORS["down"]


def _risk_color(label: str) -> str:
    return {
        "Faible": theme.COLORS["up"],
        "Modéré": theme.COLORS["warn"],
        "Élevé": theme.COLORS["down"],
    }.get(label, theme.COLORS["text_muted"])


def _save_feedback(user_id: str, row: pd.Series, rating: str,
                   pref_before: float) -> float:
    target = risk_module.feedback_to_target(float(row["risk_score"]), rating)
    pref_after = risk_module.update_pref(pref_before, target)
    fb_module.append_feedback({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "symbol": row["symbol"],
        "risk_score": float(row["risk_score"]),
        "risk_label": row["risk_label"],
        "user_rating": rating,
        "user_pref_before": pref_before,
        "user_pref_after": pref_after,
        "score": float(row["score"]),
    })
    return pref_after


def _render_reco_card(row: pd.Series, idx: int, user_id: str, pref_before: float) -> None:
    risk_color = _risk_color(row["risk_label"])
    ret_color = theme.COLORS["up"] if row["expected_return_annual"] > 0 else theme.COLORS["down"]

    st.markdown(
        f"""
        <div class="card" style="margin-bottom:0.6rem;">
          <div style="display:flex;justify-content:space-between;align-items:start;">
            <div>
              <div style="font-size:1.5rem;font-weight:800;letter-spacing:-0.01em;">{row["symbol"]}</div>
              <div class="card-sub" style="margin-top:0.1rem;">Score global <b style="color:var(--text);">{row["score"]:.2f}</b> · match {row["match_score"]:.0%}</div>
            </div>
            <span class="badge" style="background:{risk_color}22;color:{risk_color};">
              Risque {row["risk_label"]}
            </span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(2, 1fr);gap:0.5rem 0.8rem;margin-top:0.9rem;">
            <div>
              <div class="card-title">Volatilité</div>
              <div style="color:var(--text);font-weight:600;">{row['volatility_annual']*100:.1f}% / an</div>
            </div>
            <div>
              <div class="card-title">Rendement</div>
              <div style="color:{ret_color};font-weight:600;">{row['expected_return_annual']*100:+.1f}% / an</div>
            </div>
            <div>
              <div class="card-title">Max drawdown</div>
              <div style="color:var(--down);font-weight:600;">{row['max_drawdown']*100:.1f}%</div>
            </div>
            <div>
              <div class="card-title">Sharpe</div>
              <div style="color:var(--text);font-weight:600;">{row['sharpe']:.2f}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2, b3 = st.columns(3)
    sym = row["symbol"]
    if b1.button("⚠️ Trop risqué", key=f"tr_{sym}_{idx}", use_container_width=True):
        new_pref = _save_feedback(user_id, row, "too_risky", pref_before)
        st.session_state["_last_feedback"] = (sym, "too_risky", new_pref)
        st.rerun()
    if b2.button("✅ OK pour moi", key=f"ok_{sym}_{idx}", use_container_width=True, type="primary"):
        new_pref = _save_feedback(user_id, row, "good", pref_before)
        st.session_state["_last_feedback"] = (sym, "good", new_pref)
        st.rerun()
    if b3.button("🚀 Pas assez", key=f"ne_{sym}_{idx}", use_container_width=True):
        new_pref = _save_feedback(user_id, row, "not_enough_risk", pref_before)
        st.session_state["_last_feedback"] = (sym, "not_enough_risk", new_pref)
        st.rerun()


def _profile_evolution_chart(initial_pref: float, fb_df: pd.DataFrame) -> None:
    trail = risk_module.replay_history(initial_pref, fb_df)
    if not trail:
        return
    timestamps, prefs = zip(*trail)
    df = pd.DataFrame({"timestamp": timestamps, "préférence": prefs})

    fig = px.line(df, x="timestamp", y="préférence",
                  color_discrete_sequence=[theme.COLORS["primary"]])
    fig.update_traces(line=dict(width=2.5), mode="lines+markers",
                      marker=dict(size=8, color=theme.COLORS["primary"]))
    fig.add_hline(y=initial_pref, line_dash="dash",
                  line_color=theme.COLORS["text_muted"],
                  annotation_text=f"profil initial {initial_pref:.2f}",
                  annotation_position="top left")
    fig.add_hrect(y0=0, y1=0.34, fillcolor=theme.COLORS["up_soft"],
                  line_width=0, annotation_text="Prudent",
                  annotation_position="right", opacity=0.5)
    fig.add_hrect(y0=0.34, y1=0.67, fillcolor=theme.COLORS["primary_soft"],
                  line_width=0, annotation_text="Équilibré",
                  annotation_position="right", opacity=0.4)
    fig.add_hrect(y0=0.67, y1=1, fillcolor=theme.COLORS["down_soft"],
                  line_width=0, annotation_text="Audacieux",
                  annotation_position="right", opacity=0.4)
    fig.update_layout(**theme.plotly_layout(
        height=280,
        title=dict(text="Évolution de ta préférence de risque", x=0.0,
                   font=dict(size=15)),
        xaxis_title=None, yaxis_title="Préférence (0=prudent, 1=audacieux)",
        yaxis=dict(range=[0, 1], gridcolor=theme.COLORS["border"]),
    ))
    st.plotly_chart(fig, use_container_width=True)


def render() -> None:
    theme.inject_theme()

    user_id = fb_module.get_or_create_user_id(st.session_state)

    # --- Sidebar: profile + reset --------------------------------------------
    with st.sidebar:
        st.markdown("### 👤 Profil")
        st.markdown(
            f'<div class="card" style="padding:0.7rem 0.9rem;">'
            f'<div class="card-title">Identifiant session</div>'
            f'<div style="font-family:monospace;color:var(--primary);">{user_id}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("### 🎚 Profil initial")
        initial_pref = st.slider(
            "Tolérance au risque",
            0.0, 1.0,
            value=float(st.session_state.get("initial_risk_pref", 0.5)),
            step=0.05, format="%.2f",
            help="0 = très prudent · 0.5 = équilibré · 1 = audacieux. "
                 "Cette valeur sert de point de départ ; tes notations vont la faire évoluer.",
        )
        st.session_state["initial_risk_pref"] = initial_pref
        label, color = _profile_label(initial_pref)
        st.markdown(
            f'<div class="badge" style="background:{color}22;color:{color};font-size:0.85rem;'
            f'padding:0.3rem 0.7rem;">{label}</div>',
            unsafe_allow_html=True,
        )

    # --- Symbol universe -----------------------------------------------------
    df_proc = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    df_raw = data_module.load_quotes(data_module.RAW_DATA_PATH)
    syms = set()
    for d in (df_proc, df_raw):
        if "symbol" in d.columns:
            syms.update(d["symbol"].dropna().unique())
    if not syms:
        syms = set(DEFAULT_SYMBOLS)

    # --- Compute metrics + adaptation ----------------------------------------
    with st.spinner("Calcul des métriques de risque sur l'univers…"):
        metrics = _cached_universe_metrics(tuple(sorted(syms)))

    fb_df = fb_module.load_feedback(user_id=user_id)
    learned_pref = initial_pref
    for _, row in fb_df.sort_values("timestamp").iterrows():
        target = risk_module.feedback_to_target(float(row["risk_score"]),
                                                str(row["user_rating"]))
        learned_pref = risk_module.update_pref(learned_pref, target)

    label_l, color_l = _profile_label(learned_pref)

    # --- Hero ----------------------------------------------------------------
    theme.hero(
        title="🎯 Recommandations de placement",
        subtitle="Algo adaptatif : note les recommandations, ton profil de risque s'ajuste à chaque feedback.",
        status="live",
        last_update=datetime.now(timezone.utc),
    )

    # --- Profile summary cards -----------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        theme.kpi_card("Profil initial", f"{initial_pref:.2f}", sub=_profile_label(initial_pref)[0])
    with c2:
        delta = (learned_pref - initial_pref) * 100
        theme.kpi_card("Profil appris", f"{learned_pref:.2f}",
                       sub=label_l, delta=delta, delta_format="{:+.1f} pts vs initial")
    with c3:
        theme.kpi_card("Notations", f"{len(fb_df)}",
                       sub=f"User {user_id}")
    with c4:
        if not metrics.empty:
            theme.kpi_card("Univers", f"{len(metrics)} actifs",
                           sub=", ".join(sorted(metrics['symbol'].tolist()[:5])) + ("…" if len(metrics) > 5 else ""))
        else:
            theme.kpi_card("Univers", "—", sub="Pas de métriques")

    # --- Banner si feedback fraîchement enregistré ---------------------------
    last_fb = st.session_state.pop("_last_feedback", None)
    if last_fb:
        sym, rating, new_pref = last_fb
        rating_emoji = {"too_risky": "⚠️", "good": "✅", "not_enough_risk": "🚀"}[rating]
        rating_text = {"too_risky": "trop risqué", "good": "OK", "not_enough_risk": "pas assez risqué"}[rating]
        st.toast(f"{rating_emoji} {sym} noté « {rating_text} » — profil ajusté à {new_pref:.2f}",
                 icon=rating_emoji)

    if metrics.empty:
        theme.empty_state(
            "📡", "Pas encore de métriques",
            "Impossible de récupérer l'historique pour les symboles. "
            "Vérifie ta connexion réseau ou lance un entraînement ML pour précharger le cache.",
            action="`PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN`",
        )
        return

    recos = risk_module.recommend(metrics, learned_pref)

    # --- Recommendations grid (3 cols) --------------------------------------
    theme.section_header(
        "✨ Top recommandations",
        f"Trié par compatibilité avec ton profil appris ({learned_pref:.2f}).",
        right=f"Univers : {len(metrics)} actifs",
    )

    top_n = recos.head(6)
    cols = st.columns(3)
    for i, (_, row) in enumerate(top_n.iterrows()):
        with cols[i % 3]:
            _render_reco_card(row, i, user_id, learned_pref)

    # --- Profile evolution + history ----------------------------------------
    if not fb_df.empty:
        st.write("")
        theme.section_header("📈 Évolution du profil",
                             "Trajectoire reconstruite depuis le profil initial.")
        _profile_evolution_chart(initial_pref, fb_df)

        with st.expander(f"📜 Historique de tes {len(fb_df)} notations", expanded=False):
            display = fb_df[["timestamp", "symbol", "risk_label", "user_rating",
                             "user_pref_before", "user_pref_after"]].copy()
            display = display.sort_values("timestamp", ascending=False)
            display["user_rating"] = display["user_rating"].map({
                "too_risky": "⚠️ Trop risqué",
                "good": "✅ OK",
                "not_enough_risk": "🚀 Pas assez",
            })
            st.dataframe(
                display, use_container_width=True, hide_index=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Quand", format="HH:mm:ss"),
                    "symbol": st.column_config.TextColumn("Actif", width="small"),
                    "risk_label": st.column_config.TextColumn("Risque"),
                    "user_rating": st.column_config.TextColumn("Notation"),
                    "user_pref_before": st.column_config.NumberColumn("Profil avant", format="%.2f"),
                    "user_pref_after": st.column_config.NumberColumn("Profil après", format="%.2f"),
                },
            )

        if st.button("🗑️ Reset mes notations", help="Efface tes notations pour repartir de zéro."):
            n = fb_module.reset_user_feedback(user_id)
            st.toast(f"🗑 {n} notations supprimées", icon="🗑")
            st.rerun()

    # --- Full universe table -------------------------------------------------
    st.write("")
    theme.section_header("📋 Univers complet", "Toutes les métriques calculées.")
    show = recos.copy()
    show["volatility_annual"] *= 100
    show["expected_return_annual"] *= 100
    show["max_drawdown"] *= 100
    st.dataframe(
        show, use_container_width=True, hide_index=True,
        column_config={
            "symbol": st.column_config.TextColumn("Actif", width="small"),
            "risk_score": st.column_config.ProgressColumn("Score risque", format="%.2f", min_value=0, max_value=1),
            "risk_label": st.column_config.TextColumn("Niveau"),
            "volatility_annual": st.column_config.NumberColumn("Vol % / an", format="%.1f%%"),
            "expected_return_annual": st.column_config.NumberColumn("Rdt % / an", format="%+.1f%%"),
            "max_drawdown": st.column_config.NumberColumn("Max DD %", format="%.1f%%"),
            "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
            "match_score": st.column_config.ProgressColumn("Match profil", format="%.2f", min_value=0, max_value=1),
            "score": st.column_config.ProgressColumn("Score global", format="%.2f", min_value=0, max_value=1),
            "return_score": None,
            "n_obs": None,
        },
    )


render()
