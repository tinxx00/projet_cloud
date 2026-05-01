"""Pipeline view — flux de données + santé producer/consumer."""
from __future__ import annotations

import os
from datetime import timedelta, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import data as data_module
from dashboard import theme


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ingestion_rate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "ingested_at" not in df.columns:
        return pd.DataFrame()
    s = df["ingested_at"].dropna().sort_values()
    if s.empty:
        return pd.DataFrame()
    rate = s.dt.floor("min").value_counts().sort_index().reset_index()
    rate.columns = ["minute", "messages"]
    return rate


def _msgs_per_minute(status_obj) -> float:
    """Estimation simple : msgs sur les 5 dernières minutes / 5."""
    df = data_module.load_quotes(status_obj.path)
    if df.empty or "ingested_at" not in df.columns:
        return 0.0
    s = df["ingested_at"].dropna()
    if s.empty:
        return 0.0
    now = data_module.now_utc()
    window = s[s >= now - timedelta(minutes=5)]
    return float(len(window) / 5.0)


def _pill_html(status: str) -> str:
    return {
        "live": '<span class="pill pill-live"><span class="pill-dot"></span>LIVE</span>',
        "idle": '<span class="pill pill-idle"><span class="pill-dot"></span>IDLE</span>',
        "offline": '<span class="pill pill-offline"><span class="pill-dot"></span>OFFLINE</span>',
    }[status]


# ---------------------------------------------------------------------------
# Flow diagram (header section)
# ---------------------------------------------------------------------------
_FLOW_CSS = """
<style>
.flow-wrap {
  display: grid;
  grid-template-columns: repeat(5, 1fr) auto;
  align-items: stretch;
  gap: 0.45rem;
  margin: 0.6rem 0 1.2rem 0;
}
.flow-step, .flow-arrow {
  position: relative;
}
.flow-step {
  background: linear-gradient(180deg, var(--surface) 0%, var(--surface-alt) 100%);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.95rem 1rem;
  min-height: 130px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
}
.flow-step:hover {
  border-color: rgba(34, 211, 238, 0.55);
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(34, 211, 238, 0.10);
}
.flow-step.is-live { border-color: rgba(16, 185, 129, 0.45); }
.flow-step.is-idle { border-color: rgba(245, 158, 11, 0.45); }
.flow-step.is-off  { border-color: rgba(239, 68, 68, 0.4); }
.flow-step .icon {
  font-size: 1.5rem; line-height: 1;
}
.flow-step .name {
  font-weight: 700; letter-spacing: -0.01em; margin-top: 0.4rem; font-size: 1.02rem;
}
.flow-step .sub {
  color: var(--text-muted); font-size: 0.78rem; margin-top: 0.2rem;
  font-family: ui-monospace, "JetBrains Mono", Menlo, monospace;
}
.flow-step .stat {
  margin-top: 0.55rem;
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 600;
}
.flow-step .stat .num {
  color: var(--primary);
}

.flow-arrow {
  display: flex; align-items: center; justify-content: center;
  color: var(--text-muted);
  font-size: 1.4rem;
  position: relative;
}
.flow-arrow::before {
  content: "";
  position: absolute; top: 50%; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg,
    rgba(34,211,238,0) 0%,
    rgba(34,211,238,0.55) 30%,
    rgba(34,211,238,0.55) 70%,
    rgba(34,211,238,0) 100%);
  transform: translateY(-50%);
}
.flow-arrow .pulse {
  position: relative; z-index: 1;
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 12px var(--primary);
  animation: travel 2.4s ease-in-out infinite;
}
@keyframes travel {
  0%   { opacity: 0.2; transform: translateX(-22px) scale(0.7); }
  50%  { opacity: 1;   transform: translateX(0px)   scale(1.1); }
  100% { opacity: 0.2; transform: translateX(22px)  scale(0.7); }
}
</style>
"""


def _flow_diagram(raw_status, proc_status) -> None:
    """Diagramme horizontal : Finnhub → Producer → Kafka → Consumer → CSV."""
    raw_state = theme.freshness_status(raw_status.last_update)
    proc_state = theme.freshness_status(proc_status.last_update)

    raw_class = {"live": "is-live", "idle": "is-idle", "offline": "is-off"}[raw_state]
    proc_class = {"live": "is-live", "idle": "is-idle", "offline": "is-off"}[proc_state]
    # Kafka state inferred from producer (le producer publie sur Kafka)
    kafka_class = raw_class

    raw_rate = _msgs_per_minute(raw_status)
    proc_rate = _msgs_per_minute(proc_status)

    topic = os.getenv("KAFKA_TOPIC", "market.quotes.raw")
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    st.markdown(_FLOW_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="flow-wrap">
          <div class="flow-step">
            <div>
              <div class="icon">🌐</div>
              <div class="name">Finnhub API</div>
              <div class="sub">finnhub.io · /quote</div>
            </div>
            <div class="stat">Source · prix temps réel</div>
          </div>

          <div class="flow-arrow"><span class="pulse"></span></div>

          <div class="flow-step {raw_class}">
            <div>
              <div class="icon">📤</div>
              <div class="name">Producer</div>
              <div class="sub">producer.main</div>
            </div>
            <div class="stat"><span class="num">{raw_rate:.1f}</span> msg/min · {raw_status.rows:,} total</div>
          </div>

          <div class="flow-arrow"><span class="pulse"></span></div>

          <div class="flow-step {kafka_class}">
            <div>
              <div class="icon">🟧</div>
              <div class="name">Kafka topic</div>
              <div class="sub">{topic}</div>
            </div>
            <div class="stat">{bootstrap}</div>
          </div>

          <div class="flow-arrow"><span class="pulse"></span></div>

          <div class="flow-step {proc_class}">
            <div>
              <div class="icon">📥</div>
              <div class="name">Consumer</div>
              <div class="sub">consumer.main</div>
            </div>
            <div class="stat"><span class="num">{proc_rate:.1f}</span> msg/min · {proc_status.rows:,} total</div>
          </div>

          <div class="flow-arrow"><span class="pulse"></span></div>

          <div class="flow-step">
            <div>
              <div class="icon">💾</div>
              <div class="name">Storage</div>
              <div class="sub">processed_quotes.csv</div>
            </div>
            <div class="stat">{proc_status.file_size_bytes/1024:.1f} KB</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Live tape: derniers messages consommés
# ---------------------------------------------------------------------------
def _live_tape(df: pd.DataFrame, n: int = 12) -> None:
    """Affiche les n derniers messages consommés sous forme de pastilles compactes."""
    if df.empty:
        theme.empty_state("📭", "Pas encore de messages consommés",
                          "Lance le consumer pour voir les ticks arriver ici.")
        return
    cols_needed = {"symbol", "price_current", "ingested_at"}
    if not cols_needed.issubset(df.columns):
        st.info("Colonnes manquantes pour afficher la tape.")
        return

    sub = df.dropna(subset=["symbol", "price_current"]).sort_values("ingested_at").tail(n)
    rows_html = []
    for _, row in sub.iloc[::-1].iterrows():
        ts = row.get("ingested_at")
        ts_str = ts.strftime("%H:%M:%S") if pd.notna(ts) else "—"
        direction = row.get("direction", "unknown")
        delta_pct = row.get("delta_pct")
        if direction == "up":
            badge_color, arrow = theme.COLORS["up"], "▲"
        elif direction == "down":
            badge_color, arrow = theme.COLORS["down"], "▼"
        else:
            badge_color, arrow = theme.COLORS["text_muted"], "•"
        delta_str = f"{delta_pct:+.2f}%" if pd.notna(delta_pct) else "—"

        rows_html.append(
            f"""
            <div style="display:flex;align-items:center;justify-content:space-between;
                        padding:0.55rem 0.9rem;border-bottom:1px solid var(--border);
                        font-family:ui-monospace,Menlo,monospace;font-size:0.85rem;">
              <span style="color:var(--text-muted);width:78px;">{ts_str}</span>
              <span style="font-weight:700;color:var(--text);width:70px;">{row.get('symbol','?')}</span>
              <span style="color:var(--text);width:90px;text-align:right;">
                {row['price_current']:.2f}
              </span>
              <span style="color:{badge_color};font-weight:700;width:90px;text-align:right;">
                {arrow} {delta_str}
              </span>
              <span class="badge badge-flat" style="font-size:0.7rem;">
                {row.get('ingestion_mode','—')}
              </span>
            </div>
            """
        )
    st.markdown(
        f'<div class="card" style="padding:0;overflow:hidden;">{"".join(rows_html)}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Latency chart: Finnhub timestamp → ingested_at → processed_at
# ---------------------------------------------------------------------------
def _latency_chart(df: pd.DataFrame) -> None:
    if df.empty:
        st.caption("Pas de données pour calculer la latence.")
        return
    needed = {"finnhub_timestamp", "ingested_at", "processed_at"}
    if not needed.issubset(df.columns):
        st.caption("Latence non calculable : timestamps manquants dans le CSV consumer.")
        return
    sub = df.dropna(subset=list(needed)).copy()
    if sub.empty:
        st.caption("Pas de lignes avec tous les timestamps.")
        return

    # `finnhub_timestamp` est déjà converti en datetime UTC par le loader.
    sub["latence_ingestion_ms"] = (sub["ingested_at"] - sub["finnhub_timestamp"]).dt.total_seconds() * 1000
    sub["latence_traitement_ms"] = (sub["processed_at"] - sub["ingested_at"]).dt.total_seconds() * 1000
    # Garde les valeurs raisonnables uniquement
    sub = sub[(sub["latence_ingestion_ms"].between(-60000, 60_000)) &
              (sub["latence_traitement_ms"].between(-1000, 60_000))]
    if sub.empty:
        st.caption("Latences hors plage raisonnable.")
        return

    long_df = sub[["ingested_at", "latence_ingestion_ms", "latence_traitement_ms"]].melt(
        id_vars="ingested_at", var_name="étape", value_name="ms",
    )
    long_df["étape"] = long_df["étape"].map({
        "latence_ingestion_ms": "Finnhub → Producer",
        "latence_traitement_ms": "Producer → Consumer",
    })

    fig = px.scatter(
        long_df.tail(800), x="ingested_at", y="ms", color="étape",
        color_discrete_map={
            "Finnhub → Producer": theme.COLORS["primary"],
            "Producer → Consumer": theme.COLORS["warn"],
        },
        opacity=0.7,
    )
    fig.update_traces(marker=dict(size=5))
    fig.update_layout(**theme.plotly_layout(
        height=300, xaxis_title=None, yaxis_title="Latence (ms)",
        title=dict(text="Latence par étape", x=0.0, font=dict(size=14)),
        legend=dict(orientation="h", y=-0.22),
    ))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        theme.kpi_card(
            "Latence ingestion (médiane)",
            f"{sub['latence_ingestion_ms'].median():.0f} ms",
            sub=f"p95 = {sub['latence_ingestion_ms'].quantile(0.95):.0f} ms",
        )
    with c2:
        theme.kpi_card(
            "Latence traitement (médiane)",
            f"{sub['latence_traitement_ms'].median():.0f} ms",
            sub=f"p95 = {sub['latence_traitement_ms'].quantile(0.95):.0f} ms",
        )


# ---------------------------------------------------------------------------
# Stage status block (existing)
# ---------------------------------------------------------------------------
def _block(label: str, status_obj) -> None:
    sub_status = theme.freshness_status(status_obj.last_update)
    pill = _pill_html(sub_status)
    ts = status_obj.last_update.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") \
        if status_obj.last_update else "—"
    size_kb = status_obj.file_size_bytes / 1024
    st.markdown(
        f"""
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div class="card-title">{label}</div>
              <div class="card-value" style="font-size:1.3rem;">{status_obj.rows:,} lignes</div>
              <div class="card-sub">{status_obj.path} · {size_kb:.1f} KB</div>
              <div class="card-sub">Dernière ingestion : <b style="color:var(--text);">{ts}</b></div>
            </div>
            <div>{pill}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render() -> None:
    theme.inject_theme()

    raw = data_module.dataset_status(data_module.RAW_DATA_PATH)
    proc = data_module.dataset_status(data_module.PROCESSED_DATA_PATH)
    last = max([s.last_update for s in (raw, proc) if s.last_update], default=None)

    theme.hero(
        title="⚙️ Pipeline temps réel",
        subtitle="Finnhub → Producer → Kafka → Consumer → Storage. Suit chaque étape, le débit, la latence et les derniers messages consommés.",
        status=theme.freshness_status(last),
        last_update=last,
    )

    # 1) Schéma de flux animé en haut de page
    theme.section_header("🔀 Flux de données",
                        "Vue d'ensemble du parcours d'un tick depuis l'API jusqu'au stockage.")
    _flow_diagram(raw, proc)

    # 2) Cartes de statut producer / consumer
    c1, c2 = st.columns(2)
    with c1: _block("Producer (CSV brut)", raw)
    with c2: _block("Consumer (CSV traité)", proc)

    # 3) Live tape : derniers messages consommés
    st.write("")
    theme.section_header("📡 Derniers messages consommés (live tape)",
                        "Sortie directe du consumer Kafka, fenêtre glissante sur les 12 derniers ticks.")
    df_proc = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    _live_tape(df_proc, n=12)

    # 4) Débit
    st.write("")
    theme.section_header("📊 Débit d'ingestion (msgs/min)",
                        "Calculé à partir des timestamps `ingested_at`.")
    df_for_rate = data_module.load_quotes(data_module.RAW_DATA_PATH)
    if df_for_rate.empty:
        df_for_rate = df_proc
    rate = _ingestion_rate(df_for_rate)
    if rate.empty:
        theme.empty_state("📭", "Pas assez de données pour calculer le débit",
                          "Lance le producer pour quelques minutes.")
    else:
        fig = px.area(rate, x="minute", y="messages",
                      color_discrete_sequence=[theme.COLORS["primary"]])
        fig.update_traces(line=dict(width=2),
                          fillcolor=theme.COLORS["primary_soft"])
        fig.update_layout(**theme.plotly_layout(
            height=320, xaxis_title=None, yaxis_title="Messages / min",
        ))
        st.plotly_chart(fig, use_container_width=True)

    # 5) Latence
    st.write("")
    theme.section_header("⏱ Latence du pipeline",
                        "Délai entre la mesure Finnhub, l'ingestion producer et le traitement consumer.")
    _latency_chart(df_proc)

    # 6) Diagnostics
    st.write("")
    theme.section_header("🩺 Diagnostics rapides")
    diag = []
    if not raw.exists:
        diag.append(("warn", "Le CSV brut producer n'existe pas — le producer n'a pas écrit."))
    if not proc.exists:
        diag.append(("warn", "Le CSV traité consumer n'existe pas — le consumer n'a pas écrit."))
    if raw.exists and proc.exists and raw.rows > 0 and proc.rows == 0:
        diag.append(("warn", "Producer écrit mais consumer ne traite pas — vérifie la connexion Kafka."))
    if last:
        delta = (data_module.now_utc() - last).total_seconds()
        if delta > 120:
            diag.append(("warn", f"Pas de message depuis {delta:.0f}s — le pipeline semble en pause."))
        elif delta > 30:
            diag.append(("idle", f"Idle depuis {delta:.0f}s."))
        else:
            diag.append(("ok", f"Flux actif (dernier message il y a {delta:.0f}s)."))
    else:
        diag.append(("warn", "Aucun timestamp d'ingestion lisible."))

    icon = {"ok": "✅", "warn": "⚠️", "idle": "🟡"}
    for level, msg in diag:
        st.markdown(
            f"""
            <div class="card" style="margin-bottom:0.5rem;">
              <span style="font-size:1.1rem;margin-right:0.5rem;">{icon.get(level, "•")}</span>
              <span>{msg}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 7) Aperçus CSV
    st.write("")
    theme.section_header("📁 Aperçu des fichiers")
    tabs = st.tabs(["📄 Brut producer", "📄 Traité consumer"])
    with tabs[0]:
        if raw.exists and raw.rows > 0:
            df_raw = data_module.load_quotes(data_module.RAW_DATA_PATH).tail(20)
            st.dataframe(df_raw, use_container_width=True, hide_index=True)
        else:
            theme.empty_state("📁", "Fichier vide", "Aucune ligne à afficher.")
    with tabs[1]:
        if proc.exists and proc.rows > 0:
            df_proc_tail = data_module.load_quotes(data_module.PROCESSED_DATA_PATH).tail(20)
            st.dataframe(df_proc_tail, use_container_width=True, hide_index=True)
        else:
            theme.empty_state("📁", "Fichier vide", "Aucune ligne à afficher.")


render()
