"""Assistant IA commercial pour accompagner la démo et les utilisateurs finaux."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from dashboard import auth, data as data_module, llm_gateway, theme


def _market_snapshot() -> str:
    df = data_module.load_quotes(data_module.PROCESSED_DATA_PATH)
    if df.empty:
        df = data_module.load_quotes(data_module.RAW_DATA_PATH)
    if df.empty or "symbol" not in df.columns:
        return "Aucune donnée marché live disponible actuellement."

    price_col = "price_current" if "price_current" in df.columns else "price"
    if price_col not in df.columns:
        return "Aucune donnée prix exploitable actuellement."

    lines: list[str] = []
    for sym in sorted(df["symbol"].dropna().unique()):
        sub = df[df["symbol"] == sym][price_col].dropna().astype(float)
        if len(sub) < 2:
            continue
        last = float(sub.iloc[-1])
        prev = float(sub.iloc[max(0, len(sub) - 20)])
        pct = (last - prev) / (prev + 1e-9) * 100
        lines.append(f"- {sym}: {last:.2f} USD ({pct:+.2f}%)")
    return "\n".join(lines) if lines else "Données insuffisantes pour calculer une variation."


def _system_prompt(user: dict | None, snapshot: str) -> str:
    name = (user or {}).get("name", "Client")
    risk_pref = float((user or {}).get("risk_pref", 0.5))
    risk_level = "prudent" if risk_pref < 0.35 else ("audacieux" if risk_pref > 0.7 else "équilibré")

    return (
        "Tu es MarketPilot AI, un assistant d'investissement orienté business et pédagogie.\n"
        "Objectif: aider l'utilisateur à comprendre le marché et prendre des décisions claires.\n"
        "Règles:\n"
        "1) Réponse courte, structurée, concrète (3-6 points max).\n"
        "2) Ton premium, simple, non-technique.\n"
        "3) Toujours proposer une action claire (acheter/surveiller/attendre).\n"
        "4) Ne pas promettre de gains. Mentionner le risque en une phrase.\n"
        "5) Répondre en français.\n\n"
        f"Profil utilisateur: {name}, niveau de risque {risk_level} (score={risk_pref:.2f}).\n"
        f"Snapshot marché:\n{snapshot}\n\n"
        "Conclure par: 'Ce contenu est informatif et ne constitue pas un conseil financier personnalisé.'"
    )


def _starter_prompts() -> list[str]:
    return [
        "Quels sont les 3 actifs à surveiller aujourd'hui ?",
        "Donne-moi un plan prudent pour aujourd'hui.",
        "Résume le marché en 5 lignes maximum.",
        "Quels signaux sont les plus pertinents maintenant ?",
        "Fais-moi une mini stratégie 24h (entrée/sortie/risque).",
    ]


def _demo_reply(user_text: str) -> str:
    text = user_text.lower()
    if "prudent" in text or "risque" in text:
        return (
            "Voici un plan prudent en 3 actions :\n"
            "1) Prioriser les actifs stables et liquides.\n"
            "2) Entrer progressivement en 2 ou 3 temps.\n"
            "3) Définir une perte max par position avant d'entrer.\n\n"
            "Action du jour : **surveiller**, ne pas sur-allouer.\n"
            "Ce contenu est informatif et ne constitue pas un conseil financier personnalisé."
        )
    if "résume" in text or "resume" in text or "marché" in text or "marche" in text:
        return (
            "Résumé marché (format exécutif) :\n"
            "- Les mouvements restent sélectifs selon les secteurs.\n"
            "- Les opportunités existent surtout sur les actifs à momentum confirmé.\n"
            "- La discipline de risque fait la différence.\n"
            "- Les alertes permettent d'agir plus vite que la moyenne.\n"
            "- Priorité : qualité des entrées, pas quantité des trades.\n\n"
            "Action du jour : **surveiller les cassures propres**.\n"
            "Ce contenu est informatif et ne constitue pas un conseil financier personnalisé."
        )
    return (
        "Plan express recommandé :\n"
        "1) Sélectionner 3 actifs maximum à fort signal.\n"
        "2) Entrer uniquement si le signal reste confirmé.\n"
        "3) Prévoir un scénario de sortie avant l'entrée.\n\n"
        "Action du jour : **attendre la confirmation puis agir vite**.\n"
        "Ce contenu est informatif et ne constitue pas un conseil financier personnalisé."
    )


def render() -> None:
    theme.inject_theme()
    user = auth.current_user()

    theme.hero(
        title="💬 MarketPilot AI",
        subtitle="Votre coach investissement en temps réel — clair, rapide, actionnable.",
        status="live",
        last_update=datetime.now(timezone.utc),
    )

    with st.sidebar:
        st.markdown("### ⚙️ Configuration IA")
        provider = st.selectbox("Fournisseur", ["openai", "anthropic", "groq"], index=0)
        temperature = st.slider("Créativité", 0.0, 1.0, 0.3, 0.05)
        has_key = llm_gateway.has_api_key(provider)
        if has_key:
            st.success(f"API {provider.upper()} connectée")
        else:
            st.info(f"Mode démo activé (clé {provider.upper()} absente)")
        st.caption("Recommandation commerciale: OpenAI gpt-4o-mini pour le meilleur ratio qualité/coût.")

    c1, c2 = st.columns([1.4, 1])
    with c1:
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Assistant premium</div>
              <div style="font-size:1.03rem;line-height:1.7;color:var(--text);">
                Pose une question comme si tu parlais à un conseiller :
                <ul style="margin-top:0.5rem;padding-left:1.1rem;">
                  <li>"Que dois-je surveiller aujourd'hui ?"</li>
                  <li>"Je suis prudent, quel plan me proposes-tu ?"</li>
                  <li>"Quel actif a le meilleur ratio opportunité/risque ?"</li>
                </ul>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Valeur produit</div>
              <ul style="line-height:1.9;padding-left:1.1rem;color:var(--text);margin-top:0.4rem;">
                <li>Réponse instantanée</li>
                <li>Langage non technique</li>
                <li>Action claire en sortie</li>
                <li>Aligné à votre profil risque</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if "assistant_messages" not in st.session_state:
        st.session_state.assistant_messages = [
            {
                "role": "assistant",
                "content": "Bonjour 👋 Je suis MarketPilot AI. Dites-moi votre objectif du jour (protéger, optimiser, ou opportunité rapide).",
            }
        ]

    st.write("")
    theme.section_header("🧠 Conversation")

    prompt_cols = st.columns(3)
    starters = _starter_prompts()
    for i, p in enumerate(starters[:3]):
        if prompt_cols[i].button(p, use_container_width=True):
            st.session_state.assistant_messages.append({"role": "user", "content": p})
    prompt_cols2 = st.columns(2)
    for i, p in enumerate(starters[3:]):
        if prompt_cols2[i].button(p, use_container_width=True):
            st.session_state.assistant_messages.append({"role": "user", "content": p})

    for m in st.session_state.assistant_messages:
        with st.chat_message("assistant" if m["role"] == "assistant" else "user"):
            st.markdown(m["content"])

    user_input = st.chat_input("Posez votre question à MarketPilot AI…")
    if user_input:
        st.session_state.assistant_messages.append({"role": "user", "content": user_input})

    # Réponse IA si dernier message utilisateur
    if st.session_state.assistant_messages and st.session_state.assistant_messages[-1]["role"] == "user":
        if not llm_gateway.has_api_key(provider):
            # Fallback premium pour garder une démo impressionnante sans API key
            user_last = st.session_state.assistant_messages[-1]["content"]
            st.session_state.assistant_messages.append({"role": "assistant", "content": _demo_reply(user_last)})
            st.rerun()

        snapshot = _market_snapshot()
        system_prompt = _system_prompt(user, snapshot)

        with st.chat_message("assistant"):
            with st.spinner("MarketPilot AI réfléchit…"):
                try:
                    reply = llm_gateway.generate_reply(
                        provider=provider,
                        messages=st.session_state.assistant_messages,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=500,
                    )
                except Exception as exc:
                    reply = f"Je rencontre une difficulté temporaire côté IA: {exc}"
            st.markdown(reply)

        st.session_state.assistant_messages.append({"role": "assistant", "content": reply})
        st.rerun()

    st.write("")
    cta1, cta2 = st.columns([1, 1])
    if cta1.button("🧹 Nouvelle conversation", use_container_width=True):
        st.session_state.assistant_messages = [
            {
                "role": "assistant",
                "content": "Nouvelle session lancée. Quel est votre objectif aujourd'hui ?",
            }
        ]
        st.rerun()
    if cta2.button("📋 Copier le dernier conseil", use_container_width=True):
        last_assistant = next((m["content"] for m in reversed(st.session_state.assistant_messages) if m["role"] == "assistant"), "")
        st.code(last_assistant or "Aucun conseil disponible.")


render()
