# Plateforme Cloud d'Analyse Temps Réel des Marchés Financiers

Plateforme complète de collecte, traitement, prédiction et visualisation de données
boursières temps réel, déployable en local ou sur AWS.

**Pipeline :** `Finnhub → Producer → Kafka → Consumer → CSV/S3 → Dashboard Streamlit + ML`

## Fonctionnalités
- **Ingestion temps réel** : cotations Finnhub publiées en flux JSON sur Kafka, avec backup CSV et déduplication.
- **Traitement** : consumer Kafka (fallback CSV) qui enrichit chaque tick (`delta_abs`, `delta_pct`, `direction`).
- **Machine Learning** : prédiction de direction court terme (walk-forward CV, comparaison logreg/GBDT/RF/XGBoost/LightGBM, AutoML Optuna, backtest out-of-sample avec coûts).
- **Dashboard Streamlit multi-pages** : Accueil, Tendances, Opportunités, Coach IA, Activité pipeline, Recommandations, Assistant IA (LLM), Alertes, Mon compte.
- **Authentification** : login/signup, mots de passe hachés (PBKDF2 salé), préférences par utilisateur.
- **Alertes** : notifications email sur seuils de probabilité ML.
- **Assistant LLM** : passerelle OpenAI / Anthropic / Groq configurable.
- **Déploiement AWS** : EC2 (Kafka, producer/consumer, dashboard), SageMaker (entraînement), Athena (requêtes), CloudWatch (monitoring) — voir [`deploy/DEPLOIEMENT_AWS.md`](deploy/DEPLOIEMENT_AWS.md).

> 🚀 **Pour lancer le projet, suis [`LANCEMENT.md`](LANCEMENT.md).**
> Il détaille pas à pas le mode démo (sans clé API) et le mode pipeline complet
> (Kafka + producer + consumer + dashboard), ainsi que les alertes email.
>
> 📄 **Rapport complet (architecture, résultats ML, backtest, figures)** :
> [`reports/RAPPORT.md`](reports/RAPPORT.md) · [`reports/RAPPORT.pdf`](reports/RAPPORT.pdf)

## Prérequis
- **Python 3.11, 3.12 ou 3.13** (⚠️ pas 3.14 : incompatible protobuf/streamlit)
- Docker Desktop (uniquement pour le mode pipeline temps réel)
- Clé API Finnhub (uniquement pour le mode pipeline temps réel)

## Lancement rapide

**Mode démo (sans clé API, sans Docker)**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_demo_data.py
streamlit run src/dashboard/app.py
```

**Mode pipeline complet (temps réel)**
```bash
cp .env.example .env         # renseigner FINNHUB_API_KEY
docker compose up -d         # Kafka (UI sur http://localhost:8080)
PYTHONPATH=src python -m producer.main      # terminal A
PYTHONPATH=src python -m consumer.main      # terminal B
streamlit run src/dashboard/app.py          # terminal C
```

Le producer publie les cotations Finnhub sur le topic Kafka `market.quotes.raw`
(backup `data/quotes_backup.csv`). Le consumer enrichit chaque tick
(`delta_abs`, `delta_pct`, `direction`) vers `data/processed_quotes.csv`, avec
fallback CSV si Kafka est silencieux. Détails, options et variables
d'environnement : voir [`LANCEMENT.md`](LANCEMENT.md).

## Machine Learning

Ré-entraîner le modèle (walk-forward CV, comparaison de modèles, sélection auto) :
```bash
PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN \
    --period 10y --interval 1d --horizon 5 --threshold-bps 25
```

Backtester out-of-sample (train sur les 5 premières années, test sur le reste,
avec coûts de transaction, sans data leakage) :
```bash
PYTHONPATH=src python -m ml.backtest --symbols AAPL MSFT TSLA GOOGL AMZN \
    --period 10y --train-years 5 --threshold 0.55 --cost-bps 2 \
    --horizon 5 --threshold-bps-label 25
```

Sorties dans `data/models/` : `direction_model.joblib`, `training_report.json`,
`oof_predictions.csv`, `backtest_<SYMBOL>.csv`, `backtest_summary.json`.
Résultats commentés et figures : [`reports/RAPPORT.md`](reports/RAPPORT.md).

## Arborescence
- `src/producer/main.py`: boucle principale de streaming
- `src/producer/finnhub_client.py`: client Finnhub
- `src/producer/kafka_sink.py`: publication Kafka
- `src/producer/csv_sink.py`: sauvegarde CSV locale
- `src/producer/config.py`: configuration via variables d'environnement
- `src/consumer/main.py`: consumer Kafka avec fallback CSV
- `src/consumer/processor.py`: nettoyage/structuration + indicateurs
- `src/consumer/csv_fallback.py`: lecture incrémentale du CSV backup
- `src/consumer/csv_sink.py`: stockage des données traitées
- `src/consumer/config.py`: configuration du consumer
- `src/dashboard/app.py`: dashboard Streamlit (maquette)
- `src/ml/features.py`: indicateurs techniques (RSI, MACD, EMA, Bollinger, ATR, momentum)
- `src/ml/dataset.py`: téléchargement et cache de l'historique yfinance
- `src/ml/train.py`: entraînement avec walk-forward CV + comparaison logreg vs GBDT
- `src/ml/backtest.py`: backtest out-of-sample avec coûts de transaction
- `src/ml/predict.py`: prédiction live à partir des données consumer
- `docker-compose.yml`: Kafka, ZooKeeper, Kafka UI
