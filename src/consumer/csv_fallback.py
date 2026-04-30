import csv
from pathlib import Path


class CsvBackupReader:
    def __init__(self, file_path: str, start_from_end: bool = True) -> None:
        self._path = Path(file_path)
        self._last_row_index = self._count_rows() if start_from_end else 0

    def _count_rows(self) -> int:
        if not self._path.exists():
            return 0

        with self._path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            return sum(1 for _ in reader)

    def read_new_rows(self, max_rows: int) -> list[dict[str, str]]:
        if not self._path.exists():
            return []

        with self._path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))

        if self._last_row_index > len(rows):
            self._last_row_index = 0

        new_rows = rows[self._last_row_index : self._last_row_index + max_rows]
        self._last_row_index += len(new_rows)
        return new_rows
