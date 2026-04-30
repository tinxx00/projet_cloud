import csv
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CsvQuoteSink:
    FIELDNAMES = [
        "symbol",
        "price_current",
        "price_high",
        "price_low",
        "price_open",
        "price_previous_close",
        "finnhub_timestamp",
        "ingested_at",
        "source",
    ]

    def __init__(self, file_path: str) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = self._path.exists()
        self._file = self._path.open("a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.FIELDNAMES)

        if not file_exists or self._path.stat().st_size == 0:
            self._writer.writeheader()
            self._file.flush()

    def write(self, quote: dict[str, Any]) -> None:
        row = {key: quote.get(key) for key in self.FIELDNAMES}
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
        logger.info("csv_backup_closed path=%s", self._path)
