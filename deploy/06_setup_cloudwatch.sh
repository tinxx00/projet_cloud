#!/bin/bash
# =============================================================================
# 06_setup_cloudwatch.sh
# Installe l'agent CloudWatch sur une EC2 (Amazon Linux 2023)
# et configure l'envoi des logs systemd vers CloudWatch Logs.
# Usage : bash 06_setup_cloudwatch.sh <role> <log_group>
#   role      : kafka | producer-consumer | dashboard
#   log_group : nom du log group CloudWatch (ex: market-platform)
# =============================================================================
set -e

ROLE=${1:-"unknown"}
LOG_GROUP=${2:-"market-platform"}

echo "=== [1/3] Installation de l'agent CloudWatch ==="
sudo dnf install -y amazon-cloudwatch-agent

echo "=== [2/3] Configuration de l'agent ==="
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/

# Détermine les log files selon le rôle
if [ "$ROLE" = "kafka" ]; then
  LOG_STREAMS='"log_stream_name": "kafka-docker"'
  COLLECT_LIST=$(cat <<'LOGCONF'
      {
        "file_path": "/var/log/messages",
        "log_group_name": "LOG_GROUP_PLACEHOLDER",
        "log_stream_name": "kafka-system",
        "timezone": "UTC"
      }
LOGCONF
)
elif [ "$ROLE" = "producer-consumer" ]; then
  COLLECT_LIST=$(cat <<'LOGCONF'
      {
        "file_path": "/var/log/messages",
        "log_group_name": "LOG_GROUP_PLACEHOLDER",
        "log_stream_name": "producer-consumer-system",
        "timezone": "UTC"
      }
LOGCONF
)
else
  COLLECT_LIST=$(cat <<'LOGCONF'
      {
        "file_path": "/var/log/messages",
        "log_group_name": "LOG_GROUP_PLACEHOLDER",
        "log_stream_name": "dashboard-system",
        "timezone": "UTC"
      }
LOGCONF
)
fi

COLLECT_LIST=$(echo "$COLLECT_LIST" | sed "s|LOG_GROUP_PLACEHOLDER|${LOG_GROUP}/${ROLE}|g")

sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json > /dev/null <<CONFIG
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          ${COLLECT_LIST}
        ]
      }
    }
  },
  "metrics": {
    "namespace": "MarketPlatform",
    "append_dimensions": {
      "InstanceId": "\${aws:InstanceId}",
      "Role": "${ROLE}"
    },
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 60,
        "totalcpu": true
      },
      "mem": {
        "measurement": ["mem_used_percent", "mem_available_percent"],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": ["used_percent"],
        "metrics_collection_interval": 60,
        "resources": ["/"]
      },
      "net": {
        "measurement": ["bytes_sent", "bytes_recv"],
        "metrics_collection_interval": 60,
        "resources": ["eth0"]
      }
    }
  }
}
CONFIG

echo "=== [3/3] Démarrage de l'agent ==="
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s

sudo systemctl enable amazon-cloudwatch-agent
sudo systemctl start amazon-cloudwatch-agent
sudo systemctl is-active amazon-cloudwatch-agent

echo ""
echo "✅ Agent CloudWatch actif sur ${ROLE} !"
echo "   Logs  : CloudWatch Logs → ${LOG_GROUP}/${ROLE}"
echo "   Métriques : CloudWatch Metrics → MarketPlatform"
