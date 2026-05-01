from __future__ import annotations

import json
import logging
from pathlib import Path
import time
from collections import deque

from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable

from consumer.config import load_consumer_settings
from consumer.csv_fallback import CsvBackupReader
from consumer.csv_sink import ProcessedCsvSink
from consumer.processor import process_quote


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("market-consumer")


class Deduplicator:
    def __init__(self, max_size: int = 10000) -> None:
        self._max_size = max_size
        self._queue: deque[str] = deque()
        self._set: set[str] = set()

    def seen(self, key: str) -> bool:
        if key in self._set:
            return True

        self._set.add(key)
        self._queue.append(key)

        while len(self._queue) > self._max_size:
            old = self._queue.popleft()
            self._set.discard(old)

        return False



def _message_key(quote: dict) -> str:
    return f"{quote.get('symbol')}|{quote.get('finnhub_timestamp')}|{quote.get('ingested_at')}"



def _create_consumer(bootstrap_servers: str, topic: str, group_id: str) -> KafkaConsumer:
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    return consumer



def run() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    settings = load_consumer_settings()

    sink = ProcessedCsvSink(settings.processed_csv_path)
    fallback_reader = CsvBackupReader(settings.backup_csv_path, start_from_end=True)
    dedup = Deduplicator(max_size=10000)

    logger.info(
        "consumer_started topic=%s group_id=%s fallback_idle_seconds=%s",
        settings.kafka_topic,
        settings.consumer_group_id,
        settings.fallback_idle_seconds,
    )

    consumer: KafkaConsumer | None = None
    last_kafka_message_at = time.monotonic()

    try:
        while True:
            if consumer is None:
                try:
                    consumer = _create_consumer(
                        bootstrap_servers=settings.kafka_bootstrap_servers,
                        topic=settings.kafka_topic,
                        group_id=settings.consumer_group_id,
                    )
                    logger.info("kafka_consumer_connected")
                except NoBrokersAvailable:
                    logger.warning("kafka_unavailable_on_connect")
                    consumer = None

            kafka_messages_count = 0
            if consumer is not None:
                try:
                    records = consumer.poll(
                        timeout_ms=settings.consumer_poll_timeout_ms,
                        max_records=settings.fallback_batch_size,
                    )
                    for _, messages in records.items():
                        for msg in messages:
                            quote = msg.value
                            key = _message_key(quote)
                            if dedup.seen(key):
                                continue

                            processed = process_quote(quote, ingestion_mode="kafka")
                            sink.write(processed)
                            kafka_messages_count += 1
                except KafkaError as exc:
                    logger.exception("kafka_poll_failed error=%s", exc)
                    try:
                        consumer.close()
                    except Exception:  # noqa: BLE001
                        pass
                    consumer = None

            if kafka_messages_count > 0:
                last_kafka_message_at = time.monotonic()
                logger.info("kafka_messages_processed count=%s", kafka_messages_count)
                continue

            idle_seconds = time.monotonic() - last_kafka_message_at
            if idle_seconds >= settings.fallback_idle_seconds:
                fallback_rows = fallback_reader.read_new_rows(settings.fallback_batch_size)
                fallback_count = 0

                for row in fallback_rows:
                    key = _message_key(row)
                    if dedup.seen(key):
                        continue

                    processed = process_quote(row, ingestion_mode="csv_backup")
                    sink.write(processed)
                    fallback_count += 1

                if fallback_count > 0:
                    logger.warning(
                        "fallback_used source=csv_backup count=%s idle_seconds=%.1f",
                        fallback_count,
                        idle_seconds,
                    )

            time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info("consumer_stopped_by_user")
    finally:
        sink.close()
        if consumer is not None:
            consumer.close()


if __name__ == "__main__":
    run()
