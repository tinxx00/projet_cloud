# 🚀 Guide de Déploiement AWS — Market Platform

## Architecture déployée

```
[Finnhub API]
     │
     ▼
[EC2 Producer] ──► [EC2 Kafka + Zookeeper + Kafka UI]
                              │
                              ▼
                   [EC2 Consumer] ──► [S3 (CSV backup)]
                              │
                              ▼
                   [EC2 Dashboard Streamlit :8501]
```

---

## Prérequis

- Compte AWS avec accès console/CLI
- Clé SSH pour accès EC2 (`.pem`)
- Clé API Finnhub
- Repo Git du projet accessible

---

## Étape 1 — Créer les instances EC2

### Instances recommandées

| Rôle | Type EC2 | OS |
|---|---|---|
| Kafka | `t2.medium` (2 vCPU, 4 Go RAM) | Amazon Linux 2 |
| Producer + Consumer | `t2.small` | Amazon Linux 2 |
| Dashboard Streamlit | `t2.small` | Amazon Linux 2 |

> ⚠️ En **sandbox AWS Academy**, toutes les instances partagent le même VPC et utilisent le rôle `LabRole`.

---

## Étape 2 — Ouvrir les ports (Security Group)

| Instance | Port | Usage |
|---|---|---|
| Kafka EC2 | 9092 | Kafka Bootstrap |
| Kafka EC2 | 8080 | Kafka UI |
| Dashboard EC2 | 8501 | Streamlit |
| Toutes | 22 | SSH |

---

## Étape 3 — Déploiement Kafka sur EC2

1. Copier le script sur l'instance EC2 :
```bash
scp -i <ta-cle.pem> deploy/01_setup_kafka_ec2.sh ec2-user@<IP_KAFKA>:~
```

2. Se connecter en SSH et lancer le script :
```bash
ssh -i <ta-cle.pem> ec2-user@<IP_KAFKA>
bash 01_setup_kafka_ec2.sh
```

3. Vérifier que Kafka tourne :
```bash
docker ps
```

4. Ouvrir Kafka UI dans le navigateur :
```
http://<IP_KAFKA>:8080
```

---

## Étape 4 — Déploiement Producer + Consumer

1. **Editer** `deploy/02_setup_producer_consumer_ec2.sh` :
   - `REPO_URL` → ton repo Git
   - `FINNHUB_API_KEY` → ta clé API
   - `KAFKA_BOOTSTRAP_SERVERS` → IP publique de l'EC2 Kafka

2. Copier et exécuter :
```bash
scp -i <ta-cle.pem> deploy/02_setup_producer_consumer_ec2.sh ec2-user@<IP_PRODUCER>:~
ssh -i <ta-cle.pem> ec2-user@<IP_PRODUCER>
bash 02_setup_producer_consumer_ec2.sh
```

3. Vérifier les services :
```bash
sudo systemctl status finnhub-producer
sudo systemctl status market-consumer
sudo journalctl -u finnhub-producer -f
```

---

## Étape 5 — Déploiement Dashboard Streamlit

1. **Editer** `deploy/03_setup_dashboard_ec2.sh` :
   - `REPO_URL` → ton repo Git

2. Copier et exécuter :
```bash
scp -i <ta-cle.pem> deploy/03_setup_dashboard_ec2.sh ec2-user@<IP_DASHBOARD>:~
ssh -i <ta-cle.pem> ec2-user@<IP_DASHBOARD>
bash 03_setup_dashboard_ec2.sh
```

3. Accéder au dashboard :
```
http://<IP_DASHBOARD>:8501
```

---

## Étape 6 — Upload des données vers S3

1. Créer un bucket S3 dans la console AWS (ex: `market-platform-data`).

2. **Editer** `deploy/04_s3_upload.py` :
   - `BUCKET_NAME` → nom de ton bucket S3
   - `AWS_REGION` → ta région AWS

3. Installer boto3 et lancer :
```bash
pip install boto3
python3 deploy/04_s3_upload.py
```

> En sandbox AWS Academy, les credentials sont automatiquement disponibles via le rôle IAM `LabRole`.

---

## Étape 7 — Vérifications finales

| Vérification | URL / Commande |
|---|---|
| Kafka UI | `http://<IP_KAFKA>:8080` |
| Dashboard | `http://<IP_DASHBOARD>:8501` |
| Producer | `sudo journalctl -u finnhub-producer -f` |
| Consumer | `sudo journalctl -u market-consumer -f` |
| S3 bucket | Console AWS → S3 → ton bucket |

---

## Résumé des fichiers de déploiement

| Fichier | Rôle |
|---|---|
| `deploy/01_setup_kafka_ec2.sh` | Installe et lance Kafka sur EC2 |
| `deploy/02_setup_producer_consumer_ec2.sh` | Déploie producer & consumer |
| `deploy/03_setup_dashboard_ec2.sh` | Déploie le dashboard Streamlit |
| `deploy/04_s3_upload.py` | Upload les CSV sur S3 |
| `deploy/05_sagemaker_train.py` | Pipeline ML SageMaker (entraînement + déploiement modèle) |
| `deploy/sm_entry_point.py` | Script d'entraînement exécuté dans le container SageMaker |

---

## 🤖 Partie ML — SageMaker Training Job

### Architecture ML

```
[yfinance OHLCV]
      │
      ▼
[S3 bucket /training-data/]  ←── upload par 05_sagemaker_train.py
      │
      ▼
[SageMaker Training Job]  ←── SKLearn container + sm_entry_point.py
  • Walk-forward CV (TimeSeriesSplit, 5 folds)
  • LogisticRegression vs GradientBoosting
  • Sélection automatique du meilleur modèle (AUC)
      │
      ▼
[S3 /model-artifacts/model.tar.gz]
      │
      ▼
[EC2 Dashboard]  ←── SCP automatique + restart systemd
  data/models/direction_model.joblib
  data/models/training_report.json
  data/models/oof_predictions.csv
```

### Étapes

#### 1. Prérequis dans la console AWS
- Créer un bucket S3 : `market-platform-data` (région `us-east-1`)
- Créer un IAM Role SageMaker avec la policy `AmazonSageMakerFullAccess`
- Copier l'ARN du role (format : `arn:aws:iam::ACCOUNT_ID:role/NomDuRole`)

#### 2. Configurer le script

Éditer `deploy/05_sagemaker_train.py` :
```python
BUCKET_NAME   = "market-platform-data"         # ← ton bucket S3
ROLE_ARN      = "arn:aws:iam::031151181566:role/LabRole"  # ← role AWS Academy
DASHBOARD_EC2 = "98.81.248.77"                 # ← IP EC2 dashboard
```

> **Note AWS Academy** : le role disponible est généralement `LabRole`.
> ARN : `arn:aws:iam::031151181566:role/LabRole`

#### 3. Installer les dépendances locales
```bash
pip install sagemaker boto3 yfinance
```

#### 4. Lancer le pipeline ML complet
```bash
python3 deploy/05_sagemaker_train.py
```

Ce script effectue automatiquement :
1. ✅ Téléchargement des données OHLCV (yfinance, 5 ans)
2. ✅ Upload vers S3 (un CSV par symbole)
3. ✅ Lancement du Training Job SageMaker (~5-10 min)
4. ✅ Téléchargement du modèle depuis S3
5. ✅ Déploiement sur l'EC2 dashboard via SCP
6. ✅ Redémarrage automatique du service Streamlit

#### 5. Vérifier dans la console AWS
- **SageMaker** → Training Jobs → vérifier le statut `Completed`
- **S3** → `market-platform-data/market-direction/model-artifacts/`
- **Dashboard** → http://98.81.248.77:8501 → page ML
