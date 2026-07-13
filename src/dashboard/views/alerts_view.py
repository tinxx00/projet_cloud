"""Page Alertes — historique des pics détectés + configuration rapide."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_SRC = _HERE.parents[2]
_ROOT = _HERE.parents[3]
for _p in (_SRC, _ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from dashboard import auth, theme, alerts as alerts_module
from dashboard import data as data_module


def render() -> None:
    theme.inject_theme()

    user = auth.current_user()
    if not user:
        st.warning("Connectez-vous pour accéder aux alertes.")
        return

    st.markdown("## 🔔 Alertes de marché")
    st.markdown(
        "Détection automatique des **pics de hausse ou de baisse** sur vos symboles suivis. "
        "Les alertes sont vérifiées à chaque rechargement du dashboard."
    )

    # ── Configuration rapide ──────────────────────────────────────────────────
    alerts_cfg = user.get("alerts", {})
    enabled = alerts_cfg.get("enabled", False)

    with st.expander("⚙️ Configuration des alertes", expanded=not enabled):
        col1, col2 = st.columns([1, 2])
        with col1:
            new_enabled = st.toggle("Alertes activées", value=enabled)
        with col2:
            st.caption("Active la détection de pics et l'envoi d'emails.")

        symbols_available = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
        current_symbols = alerts_cfg.get("symbols", symbols_available)
        new_symbols = st.multiselect(
            "Symboles à surveiller",
            options=symbols_available,
            default=[s for s in current_symbols if s in symbols_available],
        )

        col3, col4 = st.columns(2)
        with col3:
            spike_up = st.number_input(
                "Seuil hausse (%)",
                min_value=0.1, max_value=10.0,
                value=float(alerts_cfg.get("spike_pct_up", 1.0)),
                step=0.1, format="%.1f",
                help="Alerte si le prix monte de X% sur les 10 dernières mesures.",
            )
        with col4:
            spike_down = st.number_input(
                "Seuil baisse (%)",
                min_value=0.1, max_value=10.0,
                value=float(alerts_cfg.get("spike_pct_down", 1.0)),
                step=0.1, format="%.1f",
                help="Alerte si le prix baisse de X% sur les 10 dernières mesures.",
            )

        email_input = st.text_input(
            "Email de notification",
            value=alerts_cfg.get("email", user.get("email", "")),
            placeholder="votre@email.com",
        )

        if st.button("💾 Sauvegarder la configuration", type="primary"):
            new_cfg = {
                "enabled": new_enabled,
                "symbols": new_symbols,
                "spike_pct_up": spike_up,
                "spike_pct_down": spike_down,
                "email": email_input,
                "threshold_up": 0.70,
                "threshold_down": 0.30,
            }
            auth.update_alerts(user["id"], new_cfg)
            st.success("✅ Configuration sauvegardée !")
            st.rerun()

    st.divider()

    # ── Mode démo ─────────────────────────────────────────────────────────────
    st.markdown("### 🎬 Mode démonstration")
    st.caption("Déclenche immédiatement une alerte de test vers l'email du compte connecté.")
    col_demo1, col_demo2, col_demo3 = st.columns([2, 1, 1])
    with col_demo1:
        demo_symbol = st.selectbox("Symbole", ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"],
                                   key="demo_sym", label_visibility="collapsed")
    with col_demo2:
        demo_dir = st.selectbox("Direction", ["📈 HAUSSE", "📉 BAISSE"],
                                key="demo_dir", label_visibility="collapsed")
    with col_demo3:
        if st.button("🚀 Envoyer alerte démo", type="primary", use_container_width=True):
            direction = "UP" if "HAUSSE" in demo_dir else "DOWN"
            # Vider l'anti-spam pour ce symbole/direction
            from dashboard.alerts import _load_log, _save_log, send_alert_email, _log_alert
            log = _load_log()
            log = [e for e in log if not (
                e.get("user_id") == user["id"] and
                e.get("symbol") == demo_symbol and
                e.get("direction") == direction
            )]
            _save_log(log)
            # Envoyer l'email
            sent = send_alert_email(
                to_email=user["email"],
                user_name=user.get("name", "Utilisateur"),
                symbol=demo_symbol,
                direction=direction,
                proba=0.87 if direction == "UP" else 0.13,
            )
            _log_alert(user["id"], demo_symbol, direction, 0.87 if direction == "UP" else 0.13, user["email"])
            if sent:
                st.success(f"✅ Email envoyé à **{user['email']}** !")
            else:
                st.warning("⚠️ Email non envoyé — SMTP non configuré. L'alerte est quand même enregistrée dans l'historique.")

    st.divider()

    # ── Test manuel ───────────────────────────────────────────────────────────
    st.markdown("### 🔍 Vérification automatique")
    if st.button("🔍 Vérifier les pics maintenant", use_container_width=True):
        with st.spinner("Analyse des données en cours…"):
            df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
            if df.empty:
                df = data_module.load_quotes(data_module.RAW_DATA_PATH)

            # Reload user après éventuelle sauvegarde
            user = auth.current_user()
            triggered = alerts_module.check_price_spikes(user, df)

        if triggered:
            for a in triggered:
                emoji = "🚀" if a["direction"] == "UP" else "🔻"
                color = "#10B981" if a["direction"] == "UP" else "#EF4444"
                label = "HAUSSE" if a["direction"] == "UP" else "BAISSE"
                st.markdown(
                    f"""<div style="background:{color}22;border:1px solid {color};border-radius:8px;
                                    padding:1rem;margin:0.5rem 0;">
                        <span style="font-size:1.4rem;">{emoji}</span>
                        <b style="color:{color};font-size:1.1rem;"> {a['symbol']} — {label}</b>
                        <span style="color:#94A3B8;margin-left:1rem;">{a['pct']:+.2f}%</span>
                        {"<span style='color:#10B981;margin-left:1rem;font-size:0.8rem;'>📧 Email envoyé</span>" if a.get('sent') else ""}
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.info("✅ Aucun pic détecté pour le moment.")

    # ── Affichage données live ────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📊 Prix actuels & variation")

    df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    if df.empty:
        df = data_module.load_quotes(data_module.RAW_DATA_PATH)

    price_col = "price_current" if "price_current" in df.columns else "price"
    sym_col = "symbol" if "symbol" in df.columns else None

    if not df.empty and sym_col and price_col in df.columns:
        symbols_in_data = df[sym_col].unique()
        cols = st.columns(min(len(symbols_in_data), 5))
        for i, sym in enumerate(sorted(symbols_in_data)):
            sub = df[df[sym_col] == sym][price_col].dropna().astype(float)
            if len(sub) < 2:
                continue
            last = sub.iloc[-1]
            prev = sub.iloc[max(0, len(sub) - 10)]
            pct = (last - prev) / (prev + 1e-9) * 100
            delta_color = "normal" if pct >= 0 else "inverse"
            with cols[i % 5]:
                st.metric(
                    label=sym,
                    value=f"${last:.2f}",
                    delta=f"{pct:+.2f}%",
                    delta_color=delta_color,
                )
    else:
        st.info("Aucune donnée de prix disponible.")

    # ── Historique ────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📋 Historique des alertes déclenchées")

    log = alerts_module.get_alerts_log(user_id=user["id"], limit=50)

    if not log:
        st.info("Aucune alerte enregistrée pour votre compte.")
    else:
        rows = []
        for entry in log:
            ts = entry.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts).strftime("%d/%m/%Y %H:%M")
            except Exception:
                dt = ts
            direction = entry.get("direction", "")
            emoji = "🚀" if direction == "UP" else "🔻"
            rows.append({
                "Date": dt,
                "Symbole": entry.get("symbol", ""),
                "Direction": f"{emoji} {direction}",
                "Variation": f"{entry.get('proba', 0) * 100:.1f}%",
                "Email": "✅" if entry.get("email") else "—",
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        if st.button("🗑️ Effacer l'historique", type="secondary"):
            from dashboard.alerts import ALERTS_LOG_PATH, _load_log, _save_log
            full_log = _load_log()
            filtered = [e for e in full_log if e.get("user_id") != user["id"]]
            _save_log(filtered)
            st.success("Historique effacé.")
            st.rerun()


render()
