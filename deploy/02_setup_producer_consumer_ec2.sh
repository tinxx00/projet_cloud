#!/bin/bash
# =============================================================================
# 02_setup_producer_consumer_ec2.sh
# Déploiement du producer et du consumer Finnhub sur une instance EC2
# À exécuter en SSH sur l'instance EC2 : bash 02_setup_producer_consumer_ec2.sh
# =============================================================================
set -e

# ---- VARIABLES À ADAPTER ----
REPO_URL="https://github.com/tinxx00/projet_cloud.git"
FINNHUB_API_KEY="ct4elr9r01qt5t1fprp0ct4elr9r01qt5t1fprpg"
KAFKA_BOOTSTRAP_SERVERS="172.31.40.72:9092"
SYMBOLS="AAPL,MSFT,GOOGL,AMZN,TSLA"
# -----------------------------

echo "=== [1/5] Mise à jour + Installation Python & git ==="
sudo dnf update -y
sudo dnf install -y git python3 python3-pip

echo "=== [2/5] Clonage du projet ==="
cd /home/ec2-user
if [ -d "PA" ]; then
  cd PA && git pull
else
  git clone "$REPO_URL" PA && cd PA
fi

echo "=== [3/5] Création de l'environnement Python ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [4/5] Configuration du fichier .env ==="
cat > .env <<EOF
FINNHUB_API_KEY=${FINNHUB_API_KEY}
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}
SYMBOLS=${SYMBOLS}
KAFKA_TOPIC=market.quotes.raw
BACKUP_CSV_PATH=data/quotes_backup.csv
DEDUP_ENABLED=true
FINNHUB_MAX_REQUESTS_PER_MINUTE=30
POLL_INTERVAL_SECONDS=10
EOF

echo "=== [5/5] Lancement du producer et du consumer (systemd) ==="

# Crée le service systemd pour le producer
sudo bash -c "cat > /etc/systemd/system/finnhub-producer.service" <<EOF
[Unit]
Description=Finnhub Kafka Producer
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/PA
EnvironmentFile=/home/ec2-user/PA/.env
ExecStart=/home/ec2-user/PA/.venv/bin/python -m producer.main
Environment=PYTHONPATH=/home/ec2-user/PA/src
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Crée le service systemd pour le consumer
sudo bash -c "cat > /etc/systemd/system/market-consumer.service" <<EOF
[Unit]
Description=Market Kafka Consumer
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/PA
EnvironmentFile=/home/ec2-user/PA/.env
ExecStart=/home/ec2-user/PA/.venv/bin/python -m consumer.main
Environment=PYTHONPATH=/home/ec2-user/PA/src
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable finnhub-producer market-consumer
sudo systemctl start finnhub-producer market-consumer

echo ""
echo "✅ Producer et Consumer démarrés en tant que services systemd !"
echo "   sudo systemctl status finnhub-producer"
echo "   sudo systemctl status market-consumer"
echo "   sudo journalctl -u finnhub-producer -f"
