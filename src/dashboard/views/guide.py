"""Parcours client — guide de démonstration commerciale."""
from __future__ import annotations

import streamlit as st

from dashboard import theme


def _step(title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="card" style="margin-bottom:0.8rem;">
          <div class="card-title">Étape</div>
          <div class="card-value" style="font-size:1.1rem;">{title}</div>
          <div class="card-sub" style="margin-top:0.5rem;color:var(--text);line-height:1.6;">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    theme.inject_theme()

    theme.hero(
        title="🧭 Parcours de démo",
        subtitle="Le script simple pour présenter MarketPilot comme un produit prêt à vendre.",
        status="live",
    )

    c1, c2 = st.columns([1.3, 1])
    with c1:
        theme.section_header("🎬 Démo en 5 minutes")
        _step("1) Impact immédiat", "Commence par l'Accueil : interface premium, marché en direct, valeur visible en 10 secondes.")
        _step("2) Opportunités", "Montre comment l'utilisateur identifie rapidement les mouvements importants et les actifs à surveiller.")
        _step("3) Recommandations", "Présente la personnalisation du profil de risque avec des conseils compréhensibles.")
        _step("4) Alertes email", "Déclenche une alerte live pour prouver l'utilité pratique du produit en conditions réelles.")
        _step("5) Conversion", "Conclue sur les offres Starter / Pro / Business et l'abonnement mensuel.")

    with c2:
        theme.section_header("💬 Pitch commercial")
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Message clé</div>
              <p style="line-height:1.7;color:var(--text);margin-top:0.5rem;">
                <b>MarketPilot</b> aide les investisseurs à passer de l'information brute
                à une décision claire, en quelques secondes.
              </p>
              <ul style="line-height:1.8;color:var(--text);padding-left:1.1rem;">
                <li>Simple à comprendre</li>
                <li>Utile au quotidien</li>
                <li>Actionnable immédiatement</li>
              </ul>
            </div>
            <div class="card" style="margin-top:0.8rem;">
              <div class="card-title">Arguments de vente</div>
              <ul style="line-height:1.8;color:var(--text);padding-left:1.1rem;">
                <li>Gain de temps pour l'utilisateur</li>
                <li>Réduction du stress décisionnel</li>
                <li>Suivi personnalisé et alertes proactives</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    theme.section_header("❓ Questions fréquentes client")
    faqs = [
        ("À qui s'adresse MarketPilot ?", "Aux investisseurs particuliers et équipes qui veulent une aide à la décision claire et rapide."),
        ("Quel est le bénéfice principal ?", "Repérer les opportunités plus tôt et recevoir des alertes utiles au bon moment."),
        ("L'outil est-il personnalisable ?", "Oui, les recommandations s'adaptent au profil et aux préférences de chaque utilisateur."),
        ("Peut-on l'utiliser en démonstration live ?", "Oui, l'interface est conçue pour une démonstration fluide en soutenance ou devant des prospects."),
    ]
    for q, a in faqs:
        with st.expander(q):
            st.markdown(a)


render()
