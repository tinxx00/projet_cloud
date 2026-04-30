# Pipeline boursier - Étape 1: Producer Finnhub vers Kafka

Ce workspace implémente la première étape de ton architecture:
- récupération continue des cotations via l'API Finnhub
- publication en flux JSON dans un topic Kafka
- sauvegarde locale des quotes dans un fichier CSV (backup)
- consommation des messages via un consumer avec fallback CSV

## 1) Prérequis
- Python 3.11+
- Docker Desktop (macOS)
- Clé API Finnhub

## 2) Configuration
1. Copier le fichier d'environnement:
   - `cp .env.example .env`
2. Remplir `FINNHUB_API_KEY` dans `.env`
3. Adapter `SYMBOLS` si nécessaire

## 3) Lancer Kafka
```bash
docker compose up -d
```
Kafka sera exposé sur `localhost:9092` et Kafka UI sur `http://localhost:8080`.

## 4) Installer les dépendances Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5) Lancer le producer
```bash
PYTHONPATH=src python -m producer.main
```

Chaque message publié contient:
- `symbol`
- `price_current`, `price_high`, `price_low`, `price_open`, `price_previous_close`
- `finnhub_timestamp`
- `ingested_at`
- `source`

En parallèle, les mêmes données sont sauvegardées dans `data/quotes_backup.csv`
(chemin configurable via `BACKUP_CSV_PATH`).

Pour éviter les répétitions inutiles, la déduplication des snapshots identiques
est activée par défaut (`DEDUP_ENABLED=true`).

Pour réduire les erreurs `429 Too Many Requests`, limite le débit via
`FINNHUB_MAX_REQUESTS_PER_MINUTE` (ex: `20` ou `30` sur plan gratuit).

## 6) Vérification
- Ouvrir Kafka UI sur `http://localhost:8080`
- Vérifier le topic `market.quotes.raw`
- Observer les messages en temps réel

## 7) Maquette dashboard (Streamlit)
Lancer le dashboard:
```bash
streamlit run src/dashboard/app.py
```

Le dashboard lit en continu:
- `data/quotes_backup.csv` (brut producer)
- `data/processed_quotes.csv` (traité consumer)

Le dashboard affiche:
- métriques globales (lignes, symboles, dernière ingestion)
- onglet **Marché**: courbe des prix par symbole
- onglet **Indicateurs**: variations (%) et répartition `direction`
- onglet **Tables**: derniers ticks enrichis (`delta_abs`, `delta_pct`, `ingestion_mode`)

## 8) Consumer Kafka + fallback CSV
Lancer le consumer:
```bash
PYTHONPATH=src python -m consumer.main
```

Comportement:
- le consumer lit en priorité le topic Kafka `market.quotes.raw`
- si Kafka n'envoie plus de messages pendant `CONSUMER_FALLBACK_IDLE_SECONDS`,
  il bascule temporairement sur `data/quotes_backup.csv`
- les données traitées sont écrites dans `data/processed_quotes.csv`

Champs calculés en sortie:
- `delta_abs = price_current - price_previous_close`
- `delta_pct = delta_abs / price_previous_close * 100`
- `direction` (`up`, `down`, `flat`, `unknown`)

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
- `docker-compose.yml`: Kafka, ZooKeeper, Kafka UI
