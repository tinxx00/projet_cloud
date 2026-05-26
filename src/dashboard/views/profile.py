"""Vue Profil utilisateur — gestion des alertes email, préférences, historique feedback."""
from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dashboard import auth, theme, feedback as fb_module
from dashboard.alerts import get_alerts_log, SMTP_USER, SMTP_PASS

SYMBOLS_DEFAULT = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "NVDA", "META", "JPM", "KO", "XOM"]


def render() -> None:
    user = auth.current_user()
    if not user:
        st.error("Vous devez être connecté pour accéder à cette page.")
        return

    uid = user["id"]
    theme.inject_css()

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1.5rem;">
      <div style="font-size:3rem;">👤</div>
      <div>
        <div style="font-size:1.6rem;font-weight:800;">{user['name']}</div>
        <div style="color:var(--text-muted);">{user['email']}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab_alerts, tab_pref, tab_history, tab_password = st.tabs([
        "🔔 Alertes Email", "⚖️ Profil de risque", "📊 Historique", "🔒 Sécurité"
    ])

    # ── Alertes Email ──────────────────────────────────────────────────────────
    with tab_alerts:
        theme.section_header("🔔 Alertes Email",
                             "Recevez un email quand le modèle détecte un signal fort sur vos actions.")

        alerts_cfg = user.get("alerts", {})
        enabled = st.toggle("Activer les alertes email", value=alerts_cfg.get("enabled", False))

        if enabled:
            col1, col2 = st.columns(2)
            with col1:
                thr_up = st.slider("Seuil HAUSSE (proba ≥)", 0.55, 0.95,
                                   float(alerts_cfg.get("threshold_up", 0.70)), 0.01,
                                   help="Alerte envoyée quand la probabilité de hausse dépasse ce seuil")
            with col2:
                thr_down = st.slider("Seuil BAISSE (proba ≤)", 0.05, 0.45,
                                     float(alerts_cfg.get("threshold_down", 0.30)), 0.01,
                                     help="Alerte envoyée quand la probabilité de hausse est sous ce seuil")

            selected_symbols = st.multiselect(
                "Symboles à surveiller",
                options=SYMBOLS_DEFAULT,
                default=alerts_cfg.get("symbols", ["AAPL", "MSFT"]),
            )

            # Test SMTP config
            smtp_ok = bool(SMTP_USER and SMTP_PASS)
            if not smtp_ok:
                st.warning("⚠️ Le serveur SMTP n'est pas configuré — les emails ne seront pas envoyés. "
                           "Contactez l'administrateur pour configurer SMTP_USER / SMTP_PASS.")
            else:
                st.success(f"✅ SMTP configuré — emails envoyés depuis `{SMTP_USER}`")
        else:
            thr_up = float(alerts_cfg.get("threshold_up", 0.70))
            thr_down = float(alerts_cfg.get("threshold_down", 0.30))
            selected_symbols = alerts_cfg.get("symbols", [])

        if st.button("💾 Sauvegarder les alertes", type="primary"):
            auth.update_alerts(uid, enabled, selected_symbols, thr_up, thr_down)
            st.success("Préférences d'alertes sauvegardées ✅")

        # Historique des alertes
        st.divider()
        st.markdown("#### 📋 Dernières alertes déclenchées")
        log = get_alerts_log(uid, limit=20)
        if not log:
            st.info("Aucune alerte déclenchée pour le moment.")
        else:
            df_log = pd.DataFrame(log[::-1])
            df_log["direction"] = df_log["direction"].map(
                {"UP": "🚀 HAUSSE", "DOWN": "🔻 BAISSE"})
            df_log["proba"] = (df_log["proba"] * 100).round(1).astype(str) + "%"
            df_log["sent"] = df_log["sent"].map({True: "✅", False: "❌"})
            df_log = df_log.rename(columns={
                "timestamp": "Date", "symbol": "Symbole",
                "direction": "Signal", "proba": "Probabilité", "sent": "Email"
            })
            st.dataframe(df_log[["Date", "Symbole", "Signal", "Probabilité", "Email"]],
                         use_container_width=True, hide_index=True)

    # ── Profil de risque ───────────────────────────────────────────────────────
    with tab_pref:
        theme.section_header("⚖️ Profil de risque",
                             "Ajustez votre tolérance au risque pour personnaliser les recommandations.")

        pref = float(user.get("risk_pref", 0.5))
        labels = {0: "🛡️ Très prudent", 25: "🛡️ Prudent", 50: "⚖️ Équilibré",
                  75: "🚀 Audacieux", 100: "🚀 Très audacieux"}

        new_pref = st.slider("Tolérance au risque", 0, 100, int(pref * 100), 5) / 100.0
        label = "🛡️ Prudent" if new_pref < 0.34 else ("⚖️ Équilibré" if new_pref < 0.67 else "🚀 Audacieux")
        st.markdown(f"**Profil actuel :** {label}")

        # Feedback history summary
        fb_df = fb_module.load_feedback(uid)
        if not fb_df.empty:
            n = len(fb_df)
            last = fb_df.iloc[-1]
            st.info(f"📊 {n} feedback(s) enregistré(s) · Dernier profil adapté : **{float(last['user_pref_after']):.2f}**")

        if st.button("💾 Sauvegarder le profil", type="primary"):
            auth.update_risk_pref(uid, new_pref)
            st.success("Profil de risque mis à jour ✅")

    # ── Historique feedback ────────────────────────────────────────────────────
    with tab_history:
        theme.section_header("📊 Historique de vos feedbacks",
                             "Vos évaluations de recommandations passées.")
        fb_df = fb_module.load_feedback(uid)
        if fb_df.empty:
            st.info("Aucun feedback enregistré. Commencez par noter des recommandations dans l'onglet Recommandations.")
        else:
            fb_show = fb_df.copy()
            fb_show["user_rating"] = fb_show["user_rating"].map({
                "good": "👍 OK",
                "too_risky": "⚠️ Trop risqué",
                "not_enough_risk": "📈 Pas assez risqué"
            })
            fb_show = fb_show.sort_values("timestamp", ascending=False)
            st.dataframe(fb_show[["timestamp", "symbol", "risk_label", "user_rating",
                                   "user_pref_before", "user_pref_after"]].head(50),
                         use_container_width=True, hide_index=True)

    # ── Sécurité ──────────────────────────────────────────────────────────────
    with tab_password:
        theme.section_header("🔒 Sécurité", "Modifiez votre mot de passe.")
        with st.form("change_pw"):
            old_pw = st.text_input("Mot de passe actuel", type="password")
            new_pw = st.text_input("Nouveau mot de passe", type="password")
            new_pw2 = st.text_input("Confirmer le nouveau mot de passe", type="password")
            submitted = st.form_submit_button("Changer le mot de passe", type="primary")
        if submitted:
            import hashlib
            if hashlib.sha256(old_pw.encode()).hexdigest() != user["password_hash"]:
                st.error("Mot de passe actuel incorrect.")
            elif new_pw != new_pw2:
                st.error("Les nouveaux mots de passe ne correspondent pas.")
            elif len(new_pw) < 6:
                st.error("Mot de passe trop court (min 6 caractères).")
            else:
                auth.update_user(uid, {"password_hash": hashlib.sha256(new_pw.encode()).hexdigest()})
                st.success("Mot de passe modifié ✅")


render()
