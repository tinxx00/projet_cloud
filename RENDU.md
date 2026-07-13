# MarketPilot — Plateforme Cloud d'Analyse Temps Réel des Marchés Financiers

Document de rendu — synthèse du projet, architecture, fonctionnement et déploiement.

> Plateforme complète : collecte temps réel de cotations, traitement par flux,
> prédiction de tendance par Machine Learning, dashboard interactif, alertes email
> automatiques, et déploiement cloud AWS.

---

## Sommaire
1. [Contexte & objectif](#1-contexte--objectif)
2. [Architecture](#2-architecture)
3. [Fonctionnalités](#3-fonctionnalités)
4. [Stack technique](#4-stack-technique)
5. [Structure du projet](#5-structure-du-projet)
6. [Lancement](#6-lancement)
7. [Machine Learning (SageMaker + inférence locale)](#7-machine-learning)
8. [Déploiement AWS](#8-déploiement-aws)
9. [Sécurité](#9-sécurité)
10. [Limites & perspectives](#10-limites--perspectives)

---

## 1. Contexte & objectif

Fournir, via une architecture cloud scalable, une solution **temps réel** d'analyse et de
prédiction sur des flux boursiers : accessible, fiable et facilement déployable. Le projet
couvre toute la chaîne, de l'ingestion de données jusqu'à la décision d'investissement
assistée par IA.

---

## 2. Architecture

```
[API Finnhub]
     │
     ▼
[Producer] ──► [Kafka (+ ZooKeeper + Kafka UI)] ──► [Consumer] ──► CSV / S3
                                                          │
                                                          ▼
                                          [Dashboard Streamlit + ML]
                                                          │
                                     ┌────────────────────┼────────────────────┐
                                     ▼                     ▼                     ▼
                              [Alertes email]      [Recommandations]      [Signal IA]
```

**Chaîne ML (offline + inférence locale)**
```
[yfinance OHLCV] ──► [S3 training-data] ──► [SageMaker Training Job (SKLearn)]
                                                    │
                                                    ▼
                                       [S3 model-artifacts/model.tar.gz]
                                                    │
                                                    ▼
                              [EC2 dashboard : direction_model.joblib → inférence locale]
```

- **Producer** : récupère les cotations Finnhub, publie sur Kafka, backup CSV, déduplication.
- **Kafka** : transport temps réel résilient (topic `market.quotes.raw`).
- **Consumer** : nettoie/enrichit (`delta_abs`, `delta_pct`, `direction`), écrit `processed_quotes.csv`, fallback CSV si Kafka silencieux.
- **Dashboard Streamlit** : visualisation, ML, recommandations, alertes, authentification.
- **Worker d'alertes** : service autonome qui envoie les emails sans qu'un utilisateur soit connecté.
- **AWS** : EC2 (services), S3 (données + artefacts), SageMaker (entraînement), Athena (requêtes), CloudWatch (monitoring).

---

## 3. Fonctionnalités

| Domaine | Détail |
|---|---|
| **Ingestion temps réel** | Cotations Finnhub → Kafka, backup CSV, rate-limiting, déduplication |
| **Traitement** | Consumer Kafka avec fallback CSV, enrichissement des ticks |
| **Machine Learning** | Direction court terme, walk-forward CV, comparaison de 9 modèles (LogReg, GBDT, RF, MLP, AdaBoost, ExtraTrees, XGBoost, LightGBM, Voting), AutoML Optuna, backtest out-of-sample avec coûts |
| **Dashboard multi-pages** | Accueil, Tendances, Opportunités, Coach IA, Recommandations, Signal IA, Alertes, Activité pipeline, Mon compte |
| **Authentification** | Login/signup, mots de passe hachés (PBKDF2 salé), préférences par utilisateur |
| **Alertes email** | Automatiques (worker autonome), seuils configurables, anti-spam, email de confirmation |
| **Recommandations** | Profil de risque adaptatif (feedback utilisateur), métriques (volatilité, Sharpe, drawdown) |
| **Assistant LLM** | Passerelle OpenAI / Anthropic / Groq configurable |

---

## 4. Stack technique

- **Langage** : Python 3.11–3.13
- **Streaming** : Apache Kafka (docker-compose : Kafka + ZooKeeper + Kafka UI)
- **Données** : Finnhub (live), yfinance (historique), pandas, pyarrow (parquet)
- **ML** : scikit-learn, XGBoost, LightGBM, Optuna, joblib
- **Dashboard** : Streamlit, Plotly
- **Cloud** : AWS EC2, S3, SageMaker, Athena, CloudWatch
- **Emails** : SMTP (smtplib)

---

## 5. Structure du projet

```
PA/
├── src/
│   ├── producer/        # Ingestion Finnhub → Kafka (+ backup CSV)
│   ├── consumer/        # Consommation Kafka + enrichissement
│   ├── ml/              # features, dataset, train, backtest, predict, risk, automl
│   ├── dashboard/       # app Streamlit, thème, auth, alertes, LLM, vues
│   └── alert_worker.py  # Worker d'alertes email autonome
├── deploy/              # Scripts de déploiement AWS (EC2, S3, SageMaker, Athena, CloudWatch)
├── scripts/
│   └── seed_demo_data.py # Génère des données de démo (mode sans pipeline)
├── data/                # history (parquet), models, CSV (ignorés par git)
├── docker-compose.yml   # Kafka local
├── LANCEMENT.md         # Guide de lancement pas à pas
├── DEPLOIEMENT_AWS.md   # (deploy/) Guide de déploiement AWS
└── document_cadrage.md  # Document de cadrage
```

---

## 6. Lancement

Voir **[LANCEMENT.md](LANCEMENT.md)** pour le détail. En résumé :

**Mode démo (sans clé API, sans Docker)**
```bash
python3 -m venv .venv && source .venv/bin/activate   # Python 3.11–3.13
pip install -r requirements.txt
python scripts/seed_demo_data.py
streamlit run src/dashboard/app.py
```

**Mode pipeline complet (temps réel)**
```bash
cp .env.example .env         # renseigner FINNHUB_API_KEY
docker compose up -d         # Kafka
PYTHONPATH=src python -m producer.main      # terminal A
PYTHONPATH=src python -m consumer.main      # terminal B
streamlit run src/dashboard/app.py          # terminal C
```

**Alertes email automatiques**
```bash
# .env : SMTP_USER / SMTP_PASS (Gmail : mot de passe d'application)
PYTHONPATH=src python -m alert_worker
```

---

## 7. Machine Learning

- **Entraînement sur SageMaker** : `deploy/05_sagemaker_train.py` lance un Training Job
  (container SKLearn, instance `ml.m5.large`), avec walk-forward CV et sélection automatique
  du meilleur modèle. Le modèle est stocké sur **S3** (`model-artifacts/model.tar.gz`).
- **Inférence locale** : le modèle (`direction_model.joblib`) est chargé par le dashboard et
  les prédictions sont calculées en local (scikit-learn) — **pas d'endpoint SageMaker**, donc
  aucun coût de serving continu.
- **Réentraînement local** (optionnel) :
  ```bash
  PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN --period 10y --horizon 5
  ```

---

## 8. Déploiement AWS

Voir **[deploy/DEPLOIEMENT_AWS.md](deploy/DEPLOIEMENT_AWS.md)**.

- **EC2** : instances pour Kafka, producer/consumer, dashboard (services systemd + docker-compose).
- **S3** : données brutes/traitées + artefacts de modèle.
- **SageMaker** : Training Jobs à la demande.
- **Athena** : requêtes SQL sur les données S3 (`deploy/07_athena_queries.py`).
- **CloudWatch** : logs & monitoring (`deploy/06_setup_cloudwatch.sh`).

---

## 9. Sécurité

- Mots de passe hachés en **PBKDF2-HMAC-SHA256 salé** (200k itérations).
- Secrets (`.env`), données utilisateurs (`users.json`) et logs d'alertes **exclus du dépôt** (`.gitignore`).
- Gestion des accès AWS via IAM (rôle SageMaker dédié, security groups EC2).

---

## 10. Limites & perspectives

- **Signal ML** : la prédiction de direction quotidienne reste proche du hasard (AUC ≈ 0.52),
  ce qui est attendu pour ce type de cible ; le cadrage (horizon, features, cible) est le
  principal levier d'amélioration.
- **Perspectives** : ré-entraînement planifié, API REST, sources de données additionnelles,
  passage à MSK (Kafka managé) et à un stockage base de données pour l'historique.

---

*Projet réalisé dans le cadre d'un module Cloud / Big Data — 2026.*
