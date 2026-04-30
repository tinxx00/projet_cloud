from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ConsumerSettings:
    kafka_bootstrap_servers: str
    kafka_topic: str
    consumer_group_id: str
    consumer_poll_timeout_ms: int
    fallback_idle_seconds: int
    fallback_batch_size: int
    backup_csv_path: str
    processed_csv_path: str



def load_consumer_settings() -> ConsumerSettings:
    return ConsumerSettings(
        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_topic=os.getenv("KAFKA_TOPIC", "market.quotes.raw"),
        consumer_group_id=os.getenv("CONSUMER_GROUP_ID", "market-consumer-v1"),
        consumer_poll_timeout_ms=int(os.getenv("CONSUMER_POLL_TIMEOUT_MS", "2000")),
        fallback_idle_seconds=int(os.getenv("CONSUMER_FALLBACK_IDLE_SECONDS", "10")),
        fallback_batch_size=int(os.getenv("CONSUMER_FALLBACK_BATCH_SIZE", "200")),
        backup_csv_path=os.getenv("BACKUP_CSV_PATH", "data/quotes_backup.csv"),
        processed_csv_path=os.getenv("PROCESSED_CSV_PATH", "data/processed_quotes.csv"),
    )
