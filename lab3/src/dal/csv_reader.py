"""
DAL — CSV data reader.

Reads a single CSV file row-by-row and yields `CsvRecord` objects with
attributes named after the column headers. Empty cells are normalized to
`None` for predictable downstream parsing.
"""
from __future__ import annotations

import csv
from typing import Iterable

from .interfaces import CsvRecord, ICsvDataReader


class CsvDataReader(ICsvDataReader):
    def read(self, path: str) -> Iterable[CsvRecord]:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # row 1 is the header
                cleaned = {k: (v if v not in ("", None) else None) for k, v in row.items()}
                cleaned["_row_num"] = row_num
                yield CsvRecord(**cleaned)
