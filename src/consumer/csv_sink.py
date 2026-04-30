import csv
from pathlib import Path
from typing import Any


class ProcessedCsvSink:
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
        "ingestion_mode",
        "delta_abs",
        "delta_pct",
        "direction",
        "processed_at",
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

    def write(self, row: dict[str, Any]) -> None:
        self._writer.writerow({key: row.get(key) for key in self.FIELDNAMES})
        self._file.flush()

    def close(self) -> None:
        self._file.close()
