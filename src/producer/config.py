from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    finnhub_api_key: str
    finnhub_max_requests_per_minute: int
    kafka_bootstrap_servers: str
    kafka_topic: str
    kafka_client_id: str
    backup_csv_path: str
    dedup_enabled: bool
    symbols: list[str]
    poll_interval_seconds: int
    request_timeout_seconds: int



def _parse_symbols(raw_symbols: str) -> list[str]:
    return [symbol.strip().upper() for symbol in raw_symbols.split(",") if symbol.strip()]


def _parse_bool(raw_value: str, default: bool = True) -> bool:
    value = (raw_value or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not api_key:
        raise ValueError("FINNHUB_API_KEY is required")

    symbols = _parse_symbols(os.getenv("SYMBOLS", "AAPL,MSFT"))
    if not symbols:
        raise ValueError("SYMBOLS must contain at least one ticker")

    return Settings(
        finnhub_api_key=api_key,
        finnhub_max_requests_per_minute=int(os.getenv("FINNHUB_MAX_REQUESTS_PER_MINUTE", "50")),
        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_topic=os.getenv("KAFKA_TOPIC", "market.quotes.raw"),
        kafka_client_id=os.getenv("KAFKA_CLIENT_ID", "finnhub-producer"),
        backup_csv_path=os.getenv("BACKUP_CSV_PATH", "data/quotes_backup.csv"),
        dedup_enabled=_parse_bool(os.getenv("DEDUP_ENABLED", "true"), default=True),
        symbols=symbols,
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "5")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
    )
