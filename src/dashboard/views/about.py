"""Produit — positionnement commercial et offres."""
from __future__ import annotations

import streamlit as st

from dashboard import theme


def _offer_card(name: str, price: str, target: str, points: list[str], featured: bool = False) -> None:
    border = "#A855F7" if featured else "var(--border)"
    badge = '<span class="badge badge-flat-primary" style="margin-left:0.5rem;">Recommandé</span>' if featured else ""
    items = "".join(f"<li style='margin:0.28rem 0'>{p}</li>" for p in points)
    st.markdown(
        f"""
        <div class="card" style="border-color:{border};min-height:280px;">
          <div class="card-title">Offre</div>
          <div style="display:flex;align-items:center;gap:0.3rem;">
            <div class="card-value" style="font-size:1.35rem;">{name}</div>{badge}
          </div>
          <div style="font-size:1.9rem;font-weight:900;margin-top:0.45rem;">{price}</div>
          <div class="card-sub">{target}</div>
          <ul style="margin-top:0.7rem;padding-left:1.1rem;color:var(--text);line-height:1.5;">{items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    theme.inject_theme()

    theme.hero(
        title="✨ Produit",
        subtitle="MarketPilot transforme des signaux complexes en décisions d'investissement simples.",
        status="live",
    )

    st.markdown(
        """
        <div class="card">
          <div class="card-title">Proposition de valeur</div>
          <div style="font-size:1.05rem;line-height:1.7;">
            <b>MarketPilot</b> aide les investisseurs à agir plus vite et avec plus de confiance :
            <ul style="margin-top:0.6rem;padding-left:1.2rem;">
              <li>Vision claire du marché en temps réel</li>
              <li>Recommandations adaptées au profil de risque</li>
              <li>Alertes automatiques par email sur mouvements importants</li>
              <li>Assistant IA pour prioriser les opportunités</li>
            </ul>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    theme.section_header("💼 Offres commerciales", "Exemple de packaging pour une mise en vente")

    c1, c2, c3 = st.columns(3)
    with c1:
        _offer_card(
            "Starter",
            "29€ / mois",
            "Particuliers débutants",
            [
                "Jusqu'à 5 actifs suivis",
                "Alertes email en temps réel",
                "Recommandations quotidiennes",
                "Support standard",
            ],
        )
    with c2:
        _offer_card(
            "Pro",
            "79€ / mois",
            "Investisseurs actifs",
            [
                "Jusqu'à 30 actifs suivis",
                "Assistant IA avancé",
                "Analyses et opportunités en continu",
                "Support prioritaire",
            ],
            featured=True,
        )
    with c3:
        _offer_card(
            "Business",
            "Sur devis",
            "Cabinets, équipes et partenaires",
            [
                "Multi-utilisateurs",
                "Personnalisation marque blanche",
                "SLA & onboarding dédié",
                "Accompagnement stratégique",
            ],
        )

    st.write("")
    theme.section_header("📣 Démonstration de vente", "Script court pour une soutenance ou un rendez-vous client")
    st.markdown(
        """
        <div class="card">
          <ol style="margin:0.2rem 0 0 0;padding-left:1.2rem;line-height:1.8;">
            <li><b>Montrer la page Accueil</b> : valeur immédiate, infos claires, design premium.</li>
            <li><b>Ouvrir Opportunités</b> : prouver qu'on identifie rapidement les signaux utiles.</li>
            <li><b>Afficher Recommandations</b> : démontrer la personnalisation.</li>
            <li><b>Déclencher une alerte email</b> : impact concret en direct.</li>
            <li><b>Conclure avec les offres</b> : Starter, Pro, Business.</li>
          </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    theme.section_header("❤️ Ce que le client ressent", "Preuves sociales de valeur")
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown(
            """
            <div class="card">
              <div style="font-size:1.8rem;">⭐️⭐️⭐️⭐️⭐️</div>
              <div class="card-sub" style="color:var(--text);">"Je vais droit à l'essentiel, sans me perdre dans des écrans techniques."</div>
              <div class="card-title" style="margin-top:0.7rem;">— Investisseur particulier</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with t2:
        st.markdown(
            """
            <div class="card">
              <div style="font-size:1.8rem;">⭐️⭐️⭐️⭐️⭐️</div>
              <div class="card-sub" style="color:var(--text);">"Les alertes email me font gagner un temps énorme au quotidien."</div>
              <div class="card-title" style="margin-top:0.7rem;">— Trader indépendant</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with t3:
        st.markdown(
            """
            <div class="card">
              <div style="font-size:1.8rem;">⭐️⭐️⭐️⭐️⭐️</div>
              <div class="card-sub" style="color:var(--text);">"L'assistant IA me donne un plan clair en quelques secondes."</div>
              <div class="card-title" style="margin-top:0.7rem;">— Client Pro</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    theme.section_header("🚀 Prochaine étape", "Transformer la démo en vente")
    cta1, cta2, cta3 = st.columns(3)
    with cta1:
        st.button("📅 Planifier une démo", use_container_width=True, type="primary")
    with cta2:
        st.button("💼 Recevoir une offre", use_container_width=True)
    with cta3:
        st.button("📞 Être rappelé", use_container_width=True)


render()
