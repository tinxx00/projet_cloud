#!/bin/bash
# =============================================================================
# 01_setup_kafka_ec2.sh
# Déploiement de Kafka + Zookeeper + Kafka UI sur une instance EC2 Amazon Linux 2
# À exécuter en SSH sur l'instance EC2 : bash 01_setup_kafka_ec2.sh
# =============================================================================
set -e

echo "=== [1/4] Mise à jour du système ==="
sudo dnf update -y

echo "=== [2/4] Installation de Docker ==="
sudo dnf install -y docker git
sudo service docker start
sudo usermod -aG docker ec2-user

echo "=== [3/4] Installation de Docker Compose ==="
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version

echo "=== [4/4] Démarrage de Kafka ==="
# IP privée via IMDSv2
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
EC2_PRIVATE_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/local-ipv4)
EC2_PUBLIC_IP=$(curl -s --max-time 5 http://checkip.amazonaws.com || curl -s --max-time 5 https://api.ipify.org)
echo "IP privée : $EC2_PRIVATE_IP | IP publique : $EC2_PUBLIC_IP"

# Crée le docker-compose Kafka (espaces uniquement, pas de tabs)
cat > /home/ec2-user/docker-compose.yml << COMPOSE
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.1
    container_name: zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
  kafka:
    image: confluentinc/cp-kafka:7.6.1
    container_name: kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "29092:29092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_INTERNAL:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://${EC2_PRIVATE_IP}:9092,PLAINTEXT_INTERNAL://kafka:29092
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,PLAINTEXT_INTERNAL://0.0.0.0:29092
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT_INTERNAL
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_HEAP_OPTS: "-Xmx512m -Xms256m"
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: kafka-ui
    depends_on:
      - kafka
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
COMPOSE

cd /home/ec2-user
sudo docker-compose up -d

echo ""
echo "✅ Kafka démarré avec succès !"
echo "   Kafka Bootstrap : ${EC2_PRIVATE_IP}:9092"
echo "   Kafka UI        : http://${EC2_PUBLIC_IP}:8080"
