# 🚀 Guide de lancement

Ce fichier contient **toutes les commandes** pour lancer le projet sur un PC neuf.
Deux modes sont proposés :

- **Mode démo** → aucune clé API, aucun Docker. Le dashboard s'ouvre déjà rempli. **← recommandé pour une première prise en main.**
- **Mode pipeline complet** → flux temps réel Finnhub + Kafka (nécessite Docker et une clé API Finnhub).

---

## ✅ Prérequis

- **Python 3.11, 3.12 ou 3.13**
  ⚠️ **Pas Python 3.14** : incompatible avec streamlit/protobuf (le dashboard ne démarre pas).
  Vérifier sa version :
  ```bash
  python3 --version
  ```
- (Mode complet uniquement) **Docker Desktop** installé et démarré.
- (Mode complet uniquement) Une **clé API Finnhub** gratuite : https://finnhub.io

---

## 🐳 MODE DOCKER (tout-en-un, une seule commande)

Lance **toute la stack** (Kafka + Producer + Consumer + Dashboard + Worker) d'un coup :

```bash
cp .env.example .env      # puis renseigner FINNHUB_API_KEY dans .env
docker compose up -d --build
```

➡️ Dashboard : **http://localhost:8501** · Kafka UI : **http://localhost:8080**

Pour tout arrêter :
```bash
docker compose down
```

> Nécessite **Docker Desktop**. La première construction prend quelques minutes
> (installation des dépendances). Les données (`data/`) sont partagées entre les
> conteneurs via un volume. Sans clé Finnhub, le dashboard tourne quand même sur
> les données de démo — seule l'ingestion live nécessite la clé.

---

## 🟢 MODE DÉMO (rapide, sans clé API)

### macOS / Linux
```bash
# 1. Se placer dans le dossier du projet
cd PA

# 2. Créer et activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# 3. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 4. Générer les données de démonstration (depuis l'historique fourni)
python scripts/seed_demo_data.py

# 5. Lancer le dashboard
streamlit run src/dashboard/app.py
```

### Windows (PowerShell)
```powershell
cd PA
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python scripts\seed_demo_data.py
streamlit run src/dashboard/app.py
```

➡️ Le dashboard s'ouvre sur **http://localhost:8501**
➡️ **Créer un compte** (onglet « Créer un compte ») puis se connecter. C'est tout ✅

> Les données de démo proviennent de l'historique boursier réel versionné dans
> `data/history/` (pas de connexion externe requise). Le modèle ML est déjà
> entraîné et fourni (`data/models/direction_model.joblib`).

---

## 🔵 MODE PIPELINE COMPLET (temps réel Finnhub → Kafka)

À faire **après** avoir réalisé les étapes 1 à 3 du mode démo (venv + dépendances).

```bash
# 1. Configurer la clé API
cp .env.example .env
#   puis éditer .env et renseigner FINNHUB_API_KEY=...

# 2. Démarrer Kafka (+ interface web) via Docker
docker compose up -d
#   Kafka UI dispo sur http://localhost:8080

# 3. Lancer le producer (collecte Finnhub → Kafka)   [terminal A]
PYTHONPATH=src python -m producer.main

# 4. Lancer le consumer (Kafka → CSV traité)          [terminal B]
PYTHONPATH=src python -m consumer.main

# 5. Lancer le dashboard                               [terminal C]
streamlit run src/dashboard/app.py
```

Pour tout arrêter :
```bash
docker compose down
```

---

## 🤖 (Optionnel) Réentraîner le modèle ML
```bash
PYTHONPATH=src python -m ml.train --symbols AAPL MSFT TSLA GOOGL AMZN \
    --period 10y --interval 1d --horizon 5 --threshold-bps 25
```

## 🔔 Alertes email automatiques
Un utilisateur qui **active ses alertes** dans « Mon compte » reçoit :
1. Un **email de confirmation immédiat** (dès l'activation).
2. Des **alertes automatiques** dès qu'un signal fort est détecté — **sans avoir à ouvrir l'app**.

### a) Configurer l'envoi (une fois)
Dans `.env` :
```env
SMTP_USER=votre.email@gmail.com
SMTP_PASS=mot_de_passe_application    # Gmail : https://myaccount.google.com/apppasswords
```

### b) Lancer le worker d'alertes (envoi automatique en continu)
```bash
PYTHONPATH=src python -m alert_worker
```
Ce service tourne indépendamment du dashboard : il vérifie toutes les 2 minutes les
signaux ML + pics de prix pour **tous** les comptes abonnés et envoie les emails
(anti-spam : max 1 alerte / 5 min / actif / sens). Laisse-le tourner pendant la démo.

## 💬 (Optionnel) Activer l'assistant IA (LLM)
Ajouter une clé dans `.env` selon le fournisseur voulu :
```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...
```

---

## 🆘 Problèmes fréquents

| Symptôme | Cause / Solution |
|---|---|
| `TypeError: Metaclasses with custom tp_new...` au lancement | Python 3.14 utilisé → recréer le venv avec Python 3.11–3.13. |
| Dashboard vide / « aucune donnée » | Lancer `python scripts/seed_demo_data.py` (mode démo). |
| `ModuleNotFoundError` | Vérifier que le venv est activé et `pip install -r requirements.txt` fait. |
| `pandas ... parquet` erreur | `pip install pyarrow` (déjà dans requirements.txt). |
| Producer : erreurs `429 Too Many Requests` | Baisser `FINNHUB_MAX_REQUESTS_PER_MINUTE` dans `.env` (ex : 20). |
| Kafka ne démarre pas | Vérifier que Docker Desktop est bien lancé. |
