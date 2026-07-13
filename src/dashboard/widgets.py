"""Widgets flottants : cloche de notifications (haut-droite) + Coach IA (bas-droite).

Rendus par-dessus toutes les pages via des conteneurs positionnés en `fixed`.
La configuration des alertes reste dans « Mon compte ».
"""
from __future__ import annotations

import urllib.parse

import streamlit as st

from dashboard import llm_gateway
from dashboard.alerts import get_alerts_log


# Icône robot minimaliste (traits blancs) pour le bouton flottant du Coach IA
_ROBOT_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 24 24' "
    "fill='none' stroke='#fff' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>"
    "<rect x='4.5' y='8' width='15' height='11' rx='3'/>"
    "<path d='M12 4.6V8'/><circle cx='12' cy='3.4' r='1.1'/>"
    "<circle cx='9.3' cy='13' r='1.2' fill='#fff' stroke='none'/>"
    "<circle cx='14.7' cy='13' r='1.2' fill='#fff' stroke='none'/>"
    "<path d='M9 16.4h6'/></svg>"
)
_ROBOT_URI = "data:image/svg+xml," + urllib.parse.quote(_ROBOT_SVG)


_FLOAT_CSS = """
<style>
.st-key-mp_bell { position: fixed; top: 4.2rem; right: 1.6rem; z-index: 1000; width: fit-content; }
.st-key-mp_chat { position: fixed; bottom: 1.8rem; right: 1.8rem; z-index: 1000; width: fit-content; }

/* Bouton chat = FAB rond, grand et animé */
.st-key-mp_chat [data-testid="stPopover"] button {
    width: 74px !important; height: 74px !important; padding: 0 !important;
    border-radius: 50% !important; border: none !important;
    font-size: 0 !important; color: transparent !important;
    background: url("__ROBOT_URI__") center / 42px 42px no-repeat,
                linear-gradient(135deg, #7C3AED 0%, #DB2777 100%) !important;
    box-shadow: 0 12px 34px rgba(139,92,246,0.5) !important;
    transition: transform 180ms cubic-bezier(.2,.8,.2,1), box-shadow 180ms ease !important;
    animation: mpPulse 2.6s ease-in-out infinite;
}
.st-key-mp_chat [data-testid="stPopover"] button:hover {
    transform: scale(1.09) !important;
    box-shadow: 0 18px 44px rgba(219,39,119,0.55) !important;
}
@keyframes mpPulse {
    0%, 100% { box-shadow: 0 12px 34px rgba(139,92,246,0.5), 0 0 0 0 rgba(139,92,246,0.35); }
    50%      { box-shadow: 0 12px 34px rgba(139,92,246,0.5), 0 0 0 14px rgba(139,92,246,0); }
}

/* Cloche = bouton rond assorti */
.st-key-mp_bell [data-testid="stPopover"] button {
    height: 46px !important; border-radius: 999px !important; font-weight: 800 !important;
    font-size: 1.05rem !important; padding: 0 0.9rem !important;
    background: var(--surface) !important; border: 1px solid var(--border) !important;
    box-shadow: 0 6px 20px rgba(139,92,246,0.22) !important;
    transition: transform 160ms ease, box-shadow 160ms ease !important;
}
.st-key-mp_bell [data-testid="stPopover"] button:hover {
    transform: translateY(-1px) !important; box-shadow: 0 10px 26px rgba(139,92,246,0.3) !important;
}
.mp-chat-u { background: rgba(139,92,246,0.12); border-radius: 10px; padding: 0.5rem 0.7rem;
    margin: 0.3rem 0 0.3rem 1.4rem; font-size: 0.86rem; color: var(--text); }
.mp-chat-a { background: var(--surface-alt); border: 1px solid var(--border); border-radius: 10px;
    padding: 0.5rem 0.7rem; margin: 0.3rem 1.4rem 0.3rem 0; font-size: 0.86rem; color: var(--text); }
.mp-notif { border-bottom: 1px solid var(--border); padding: 0.5rem 0.1rem; font-size: 0.86rem; color: var(--text); }
.mp-notif:last-child { border-bottom: none; }
</style>
"""


def _demo_reply(text: str) -> str:
    t = text.lower()
    if "prudent" in t or "risque" in t:
        return ("**Plan prudent :**\n\n1) Privilégier les actifs stables et liquides.\n"
                "2) Entrer progressivement (2-3 temps).\n3) Fixer une perte max avant d'entrer.\n\n"
                "Action : **surveiller**.\n\n*Informatif — pas un conseil financier.*")
    if "résume" in t or "resume" in t or "march" in t:
        return ("**Résumé marché :**\n\n- Mouvements sélectifs selon les secteurs.\n"
                "- Opportunités sur le momentum confirmé.\n- La discipline de risque prime.\n\n"
                "Action : **surveiller les cassures propres**.\n\n*Informatif — pas un conseil financier.*")
    return ("**Plan express :**\n\n1) 3 actifs max à fort signal.\n2) Entrer seulement si confirmé.\n"
            "3) Prévoir la sortie avant l'entrée.\n\nAction : **attendre la confirmation, puis agir vite**.\n\n"
            "*Informatif — pas un conseil financier.*")


def _reply(messages: list[dict], user: dict | None) -> str:
    provider = "openai"
    if not llm_gateway.has_api_key(provider):
        return _demo_reply(messages[-1]["content"])
    system = ("Tu es MarketPilot AI, coach investissement. Réponses courtes (3-5 points), ton premium et "
              "non technique, une action claire en sortie, mention du risque, en français. "
              "Termine par un court disclaimer.")
    try:
        return llm_gateway.generate_reply(provider, messages, system, temperature=0.3, max_tokens=400)
    except Exception as exc:
        return f"Difficulté IA temporaire : {exc}"


def render_floating(user: dict | None) -> None:
    """Injecte la cloche (notifications) et le Coach IA flottant."""
    st.markdown(_FLOAT_CSS.replace("__ROBOT_URI__", _ROBOT_URI), unsafe_allow_html=True)
    uid = (user or {}).get("id", "anonymous")

    # ── Cloche notifications (haut-droite) ─────────────────────────────────
    log = get_alerts_log(uid, limit=8)
    with st.container(key="mp_bell"):
        with st.popover(f"🔔 {len(log)}" if log else "🔔"):
            st.markdown("**Notifications**")
            if not log:
                st.caption("Aucune alerte pour le moment.")
            else:
                for e in log:
                    emoji = "🚀" if e.get("direction") == "UP" else "🔻"
                    when = str(e.get("timestamp", ""))[11:16]
                    st.markdown(
                        f'<div class="mp-notif">{emoji} <b>{e.get("symbol","?")}</b> — '
                        f'{e.get("direction","")} · {when} UTC</div>',
                        unsafe_allow_html=True,
                    )
            st.caption("⚙️ Gérez vos alertes dans « Mon compte ».")

    # ── Coach IA flottant (bas-droite) ─────────────────────────────────────
    if "mp_chat_msgs" not in st.session_state:
        st.session_state.mp_chat_msgs = [{
            "role": "assistant",
            "content": "Bonjour 👋 Je suis votre **Coach IA**. Quel est votre objectif du jour ?",
        }]
    with st.container(key="mp_chat"):
        with st.popover(" "):
            st.markdown("**💬 Coach IA** — votre conseiller en temps réel")
            with st.form("mp_chat_form", clear_on_submit=True):
                q = st.text_input("Question", placeholder="Que dois-je surveiller aujourd'hui ?",
                                  label_visibility="collapsed")
                sent = st.form_submit_button("Envoyer", use_container_width=True, type="primary")
            if sent and q.strip():
                st.session_state.mp_chat_msgs.append({"role": "user", "content": q.strip()})
                st.session_state.mp_chat_msgs.append(
                    {"role": "assistant", "content": _reply(st.session_state.mp_chat_msgs, user)})
            for m in st.session_state.mp_chat_msgs[-8:]:
                cls = "mp-chat-a" if m["role"] == "assistant" else "mp-chat-u"
                st.markdown(f'<div class="{cls}">{m["content"]}</div>', unsafe_allow_html=True)
