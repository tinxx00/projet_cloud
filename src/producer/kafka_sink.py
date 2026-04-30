import json
import logging

from kafka import KafkaProducer

logger = logging.getLogger(__name__)


class KafkaQuoteSink:
    def __init__(self, bootstrap_servers: str, client_id: str) -> None:
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8"),
            acks="all",
            retries=5,
            linger_ms=50,
        )

    def publish(self, topic: str, symbol: str, payload: dict) -> None:
        future = self._producer.send(topic=topic, key=symbol, value=payload)
        metadata = future.get(timeout=10)
        logger.info(
            "message_sent topic=%s partition=%s offset=%s symbol=%s",
            metadata.topic,
            metadata.partition,
            metadata.offset,
            symbol,
        )

    def flush(self) -> None:
        self._producer.flush()
