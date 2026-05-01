"""About view — project info, stack, credits."""
from __future__ import annotations

import streamlit as st

from dashboard import theme


def render() -> None:
    theme.inject_theme()

    theme.hero(
        title="ℹ️ À propos",
        subtitle="Projet Cloud — plateforme d'analyse temps réel des marchés.",
        status="live",
    )

    c1, c2 = st.columns([1.4, 1])
    with c1:
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Vision</div>
              <p style="margin-top:0.6rem;line-height:1.6;color:var(--text);">
                Une plateforme cloud moderne pour <b>collecter, traiter, analyser et visualiser</b>
                en temps réel des données boursières, avec un module ML pour orienter
                le signal directionnel court terme.
              </p>
              <div class="card-title" style="margin-top:1rem;">Architecture</div>
              <pre style="background:var(--bg);padding:0.8rem;border-radius:8px;color:var(--text);overflow:auto;">
[Finnhub API] → [Producer Kafka] → [Kafka MSK] → [Consumer]
                                                    ↓
                                       [CSV / S3 / Postgres]
                                                    ↓
                                       [Dashboard Streamlit + ML]</pre>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="card">
              <div class="card-title">Stack technique</div>
              <ul style="margin-top:0.6rem;line-height:1.9;color:var(--text);padding-left:1.1rem;">
                <li>Python 3.11 · Pandas · NumPy</li>
                <li>Kafka + ZooKeeper (docker)</li>
                <li>Streamlit · Plotly</li>
                <li>scikit-learn · joblib</li>
                <li>yfinance (historique)</li>
              </ul>
            </div>
            <div class="card" style="margin-top:0.8rem;">
              <div class="card-title">Liens</div>
              <ul style="margin-top:0.6rem;line-height:1.8;padding-left:1.1rem;">
                <li>API : <a href="https://finnhub.io" target="_blank">finnhub.io</a></li>
                <li>Kafka UI : <a href="http://localhost:8080" target="_blank">localhost:8080</a></li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    theme.section_header("Démarrage rapide")
    st.code(
        "# 1. Lancer Kafka\n"
        "docker compose up -d\n\n"
        "# 2. Installer les deps\n"
        "pip install -r requirements.txt\n\n"
        "# 3. Producer + Consumer\n"
        "PYTHONPATH=src python -m producer.main\n"
        "PYTHONPATH=src python -m consumer.main\n\n"
        "# 4. Dashboard\n"
        "streamlit run src/dashboard/app.py",
        language="bash",
    )

    st.markdown(
        """
        <div style="text-align:center;color:var(--text-muted);margin-top:2rem;font-size:0.8rem;">
          © 2026 Market Platform · Projet Cloud FinTech
        </div>
        """,
        unsafe_allow_html=True,
    )


render()
