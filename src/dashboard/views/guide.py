"""Guide view — comment utiliser chaque section du dashboard."""
from __future__ import annotations

import streamlit as st

from dashboard import theme


TABS = [
    {
        "emoji": "🏠",
        "name": "Accueil",
        "purpose": "Point d'entrée — vue d'ensemble du pipeline et raccourcis vers les autres sections.",
        "shows": [
            "Statut live du producer et du consumer (LIVE / IDLE / OFFLINE)",
            "Compteurs : lignes brutes, lignes traitées, symboles actifs, dernière ingestion",
            "Cartes de navigation rapides vers Marché, Analyse, Pipeline, Signal IA",
        ],
        "tips": [
            "Si tu vois OFFLINE partout, le pipeline n'est pas encore lancé.",
            "L'horloge \"dernière ingestion\" se met à jour automatiquement.",
        ],
    },
    {
        "emoji": "📈",
        "name": "Marché",
        "purpose": "Suivi temps réel des prix : cours actuels, chandeliers, derniers ticks.",
        "shows": [
            "KPI cards par symbole (prix courant, Δ %, badge UP/DOWN/FLAT)",
            "Courbe d'évolution des prix multi-symbole",
            "Chandeliers OHLC par symbole",
            "Table des derniers ticks avec timestamp",
        ],
        "controls": [
            "Toggle **Rafraîchissement live** : actualise tout sans recharger la page",
            "Slider **Intervalle (s)** : 2 à 30 secondes",
            "Multiselect **Symboles** : choisir les actifs à afficher",
            "Slider **Profondeur** : nombre de lignes à charger",
            "Radio **Source** : `processed` (consumer enrichi), `raw` (producer brut), `both`",
        ],
        "tips": [
            "Si tu n'as pas encore de chandeliers, attends quelques minutes — il faut plusieurs ticks.",
            "Le mode `both` permet de comparer ce qui sort du producer vs du consumer.",
        ],
    },
    {
        "emoji": "🔬",
        "name": "Analyse",
        "purpose": "Indicateurs et statistiques agrégées sur les données consumer.",
        "shows": [
            "🏆 Leaderboard : top 5 hausses et top 5 baisses",
            "Histogramme de distribution des variations en %",
            "Pie chart des directions (up / down / flat)",
            "Bar chart de variation actuelle par symbole avec gradient rouge↔vert",
        ],
        "controls": [
            "Multiselect des symboles à inclure",
            "Slider de la fenêtre d'analyse (50 à 5000 lignes)",
        ],
    },
    {
        "emoji": "⚙️",
        "name": "Pipeline",
        "purpose": "Comprendre et superviser le flux de données complet, du tick Finnhub jusqu'au CSV.",
        "shows": [
            "**Schéma de flux animé** : Finnhub → Producer → Kafka → Consumer → Storage avec compteurs msgs/min à chaque étape",
            "**Live tape** : 12 derniers messages consommés avec timestamp / prix / direction",
            "**Débit d'ingestion** : aire chart messages/min",
            "**Latence** : scatter Finnhub→Producer et Producer→Consumer + KPI médiane et p95",
            "Diagnostics automatiques (✅ / ⚠️ / 🟡)",
            "Aperçu des 20 dernières lignes des CSV brut et traité",
        ],
        "tips": [
            "Le schéma de flux change de couleur (vert/jaune/rouge) selon l'état de chaque étape.",
            "Les pulsations animées sur les flèches ne sont actives que si le pipeline reçoit des données.",
        ],
    },
    {
        "emoji": "🎯",
        "name": "Recommandations",
        "purpose": "Algo de placement personnalisé qui apprend tes préférences de risque.",
        "shows": [
            "Profil **initial** (slider sidebar 0..1) et profil **appris** (calculé depuis ton historique de notations)",
            "Top 6 placements scorés selon ton profil avec : volatilité, rendement annuel, max drawdown, Sharpe",
            "3 boutons par carte : **⚠️ Trop risqué**, **✅ OK pour moi**, **🚀 Pas assez**",
            "Évolution du profil au fil du temps avec bandes Prudent / Équilibré / Audacieux",
            "Historique complet de tes notations",
            "Univers complet avec barres de progression `risk_score`, `match_score`, `score`",
        ],
        "how": [
            "Chaque feedback déplace ton profil via une moyenne exponentielle :",
            "  • **Trop risqué** → cible = `risk_score - 0.15`",
            "  • **OK** → cible = `risk_score` (renforce)",
            "  • **Pas assez** → cible = `risk_score + 0.15`",
            "Profil ajusté = `profil + 0.35 × (cible - profil)`, clampé sur [0, 1]",
            "Toutes les notations sont sauvegardées dans `data/user_feedback.csv` → dataset réutilisable.",
        ],
    },
    {
        "emoji": "🤖",
        "name": "Signal IA",
        "purpose": "Modèle de classification directionnel court terme + scoring live.",
        "shows": [
            "**Model Card** : modèle chargé, taille fichier, âge, univers d'entraînement, # features",
            "**Performance** : ROC AUC, accuracy, F1 issus du walk-forward CV",
            "**Backtest interactif** : holdout temporel strict (entraînement / test séparés)",
            "  → équity curve stratégie vs B&H, Sharpe, max drawdown, hit rate",
            "**Prédiction live auto-refreshée** : probabilité haussière + signal LONG/FLAT sur la dernière barre",
        ],
        "controls": [
            "Sidebar **Auto-refresh** + **Intervalle** : refresh fragment-only (n'invalide pas les autres sections)",
            "Backtest : symbole, période, années entraînement, seuil long, coût bps, horizon, seuil label",
            "Live : symbole, fréquence d'agrégation (1min / 5min / 15min)",
        ],
        "prereq": [
            "Avoir lancé `PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN`",
            "Le modèle est lu depuis `data/models/direction_model.joblib`",
        ],
    },
    {
        "emoji": "ℹ️",
        "name": "À propos",
        "purpose": "Vision du projet, stack technique et démarrage rapide.",
        "shows": ["Architecture en ASCII", "Liste des dépendances", "Snippet de démarrage"],
    },
]


def _tab_card(t: dict) -> None:
    sections = []

    def _ul(title: str, items: list[str]) -> str:
        lis = "".join(f"<li style='margin:0.18rem 0;'>{x}</li>" for x in items)
        return (
            f'<div style="margin-top:0.7rem;">'
            f'<div class="card-title">{title}</div>'
            f'<ul style="margin:0.3rem 0 0 0;padding-left:1.1rem;color:var(--text);'
            f'font-size:0.92rem;line-height:1.55;">{lis}</ul>'
            f'</div>'
        )

    if t.get("shows"):     sections.append(_ul("Ce que tu vois", t["shows"]))
    if t.get("controls"):  sections.append(_ul("Contrôles disponibles", t["controls"]))
    if t.get("how"):       sections.append(_ul("Comment ça marche", t["how"]))
    if t.get("prereq"):    sections.append(_ul("Prérequis", t["prereq"]))
    if t.get("tips"):      sections.append(_ul("💡 Astuces", t["tips"]))

    body = "".join(sections)
    st.markdown(
        f"""
        <div class="card" style="margin-bottom:0.8rem;">
          <div style="display:flex;align-items:center;gap:0.7rem;">
            <div style="font-size:1.9rem;line-height:1;">{t["emoji"]}</div>
            <div>
              <div style="font-weight:800;font-size:1.2rem;letter-spacing:-0.01em;">{t["name"]}</div>
              <div class="card-sub" style="margin-top:0.1rem;">{t["purpose"]}</div>
            </div>
          </div>
          {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    theme.inject_theme()

    theme.hero(
        title="📚 Guide d'utilisation",
        subtitle="Comment naviguer dans le dashboard et que faire dans chaque section.",
        status="live",
    )

    # --- Démarrage rapide ----------------------------------------------------
    theme.section_header("🚀 Démarrage rapide", "5 étapes pour avoir le dashboard pleinement fonctionnel.")
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.code(
            "# 1. Lancer Kafka (ZooKeeper + broker + UI)\n"
            "docker compose up -d\n\n"
            "# 2. Installer les deps Python\n"
            "pip install -r requirements.txt\n\n"
            "# 3. Démarrer le producer (ingère Finnhub → Kafka)\n"
            "PYTHONPATH=src python -m producer.main\n\n"
            "# 4. Démarrer le consumer (Kafka → CSV traité)\n"
            "PYTHONPATH=src python -m consumer.main\n\n"
            "# 5. (Optionnel) Entraîner le modèle ML\n"
            "PYTHONPATH=src python -m ml.train \\\n"
            "    --symbols AAPL MSFT TSLA GOOGL AMZN\n\n"
            "# Le dashboard est servi sur http://localhost:8501\n"
            "streamlit run src/dashboard/app.py",
            language="bash",
        )
    with c2:
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Ordre conseillé</div>
              <ol style="margin-top:0.6rem;line-height:1.8;color:var(--text);padding-left:1.1rem;">
                <li><b>Pipeline</b> → vérifier que tout est vert</li>
                <li><b>Marché</b> → voir les prix en temps réel</li>
                <li><b>Analyse</b> → comparer les symboles</li>
                <li><b>Recommandations</b> → noter pour adapter ton profil</li>
                <li><b>Signal IA</b> → backtest + prédictions live</li>
              </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- Description par tab ------------------------------------------------
    st.write("")
    theme.section_header("🗂 Les sections une par une",
                         "Chaque tab a une fonction précise. Voici tout ce qu'il faut savoir.")

    cols = st.columns(2)
    for i, t in enumerate(TABS):
        with cols[i % 2]:
            _tab_card(t)

    # --- FAQ -----------------------------------------------------------------
    st.write("")
    theme.section_header("❓ FAQ")

    faqs = [
        ("Le dashboard est vide, que faire ?",
         "Lance d'abord le producer puis le consumer pour générer `data/quotes_backup.csv` et `data/processed_quotes.csv`. "
         "Sans ces fichiers, les vues affichent un état vide explicite."),
        ("La vue Signal IA dit \"Aucun modèle entraîné\"",
         "Lance `PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN`. "
         "Le modèle sera sauvegardé dans `data/models/direction_model.joblib` et la vue se peuplera automatiquement."),
        ("Comment savoir si Kafka tourne ?",
         "Va dans la vue Pipeline : le schéma de flux indique LIVE/IDLE/OFFLINE pour chaque étape. "
         "Tu peux aussi ouvrir Kafka UI sur http://localhost:8080."),
        ("Mes notations dans Recommandations sont-elles persistantes ?",
         "Oui, elles sont append-only dans `data/user_feedback.csv` avec ton `user_id` de session. "
         "Le bouton **Reset mes notations** en supprime uniquement les tiennes."),
        ("Les rafraîchissements live consomment beaucoup ?",
         "Non — Streamlit utilise des **fragments** qui ne réexécutent que la zone live, "
         "pas toute la page. Les caches sur les CSV s'invalident sur changement de mtime/size."),
        ("Comment changer la liste des symboles suivis ?",
         "Edite `SYMBOLS` dans ton `.env` (ex. `SYMBOLS=AAPL,MSFT,TSLA,GOOGL,AMZN,NVDA`) puis relance le producer. "
         "Le dashboard les détectera automatiquement."),
    ]
    for q, a in faqs:
        with st.expander(q):
            st.markdown(a)


render()
