import logging
from pathlib import Path
import time

from dotenv import load_dotenv

from producer.config import load_settings
from producer.csv_sink import CsvQuoteSink
from producer.finnhub_client import FinnhubClient, RateLimitError
from producer.kafka_sink import KafkaQuoteSink


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("finnhub-producer")


def _quote_signature(quote: dict) -> tuple:
    return (
        quote.get("symbol"),
        quote.get("price_current"),
        quote.get("price_high"),
        quote.get("price_low"),
        quote.get("price_open"),
        quote.get("price_previous_close"),
        quote.get("finnhub_timestamp"),
    )



def run() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    settings = load_settings()

    finnhub_client = FinnhubClient(
        api_key=settings.finnhub_api_key,
        timeout_seconds=settings.request_timeout_seconds,
    )
    kafka_sink = KafkaQuoteSink(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.kafka_client_id,
    )
    csv_sink = CsvQuoteSink(file_path=settings.backup_csv_path)

    logger.info(
        "producer_started topic=%s symbols=%s interval=%ss backup_csv=%s dedup_enabled=%s rpm_limit=%s",
        settings.kafka_topic,
        settings.symbols,
        settings.poll_interval_seconds,
        settings.backup_csv_path,
        settings.dedup_enabled,
        settings.finnhub_max_requests_per_minute,
    )
    last_signatures: dict[str, tuple] = {}
    min_seconds_between_requests = 60.0 / max(1, settings.finnhub_max_requests_per_minute)
    last_request_ts = 0.0

    try:
        while True:
            for symbol in settings.symbols:
                try:
                    elapsed = time.monotonic() - last_request_ts
                    if elapsed < min_seconds_between_requests:
                        time.sleep(min_seconds_between_requests - elapsed)

                    quote = finnhub_client.fetch_quote(symbol)
                    last_request_ts = time.monotonic()
                    signature = _quote_signature(quote)
                    if settings.dedup_enabled and last_signatures.get(symbol) == signature:
                        logger.debug("quote_unchanged_skip symbol=%s", symbol)
                        continue
                    last_signatures[symbol] = signature

                    try:
                        csv_sink.write(quote)
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("csv_backup_failed symbol=%s error=%s", symbol, exc)

                    kafka_sink.publish(settings.kafka_topic, symbol, quote)
                except RateLimitError as exc:
                    cooldown = exc.retry_after_seconds if exc.retry_after_seconds is not None else max(5.0, min_seconds_between_requests * 2)
                    logger.warning("finnhub_rate_limited symbol=%s cooldown_seconds=%.1f", symbol, cooldown)
                    time.sleep(cooldown)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("publish_failed symbol=%s error=%s", symbol, exc)

            kafka_sink.flush()
            time.sleep(settings.poll_interval_seconds)
    finally:
        csv_sink.close()


if __name__ == "__main__":
    run()
