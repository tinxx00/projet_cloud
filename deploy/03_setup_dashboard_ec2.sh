#!/bin/bash
# =============================================================================
# 03_setup_dashboard_ec2.sh
# Déploiement du dashboard Streamlit sur une instance EC2
# À exécuter en SSH sur l'instance EC2 : bash 03_setup_dashboard_ec2.sh
# =============================================================================
set -e

# ---- VARIABLES À ADAPTER ----
REPO_URL="https://github.com/tinxx00/projet_cloud.git"
# -----------------------------

echo "=== [1/4] Mise à jour + Installation Python & git ==="
sudo dnf update -y
sudo dnf install -y git python3 python3-pip

echo "=== [2/4] Clonage du projet ==="
cd /home/ec2-user
if [ -d "PA" ]; then
  cd PA && git pull
else
  git clone "$REPO_URL" PA && cd PA
fi

echo "=== [3/4] Création de l'environnement Python ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [4/4] Création du service systemd Streamlit ==="

sudo bash -c "cat > /etc/systemd/system/streamlit-dashboard.service" <<EOF
[Unit]
Description=Market Platform Streamlit Dashboard
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/PA
ExecStart=/home/ec2-user/PA/.venv/bin/streamlit run src/dashboard/app.py \
  --server.port=8501 \
  --server.address=0.0.0.0 \
  --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable streamlit-dashboard
sudo systemctl start streamlit-dashboard

EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo ""
echo "✅ Dashboard Streamlit démarré !"
echo "   Accès : http://${EC2_PUBLIC_IP}:8501"
echo ""
echo "⚠️  N'oublie pas d'ouvrir le port 8501 dans le groupe de sécurité AWS !"
