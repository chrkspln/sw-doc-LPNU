"""
File output strategy.

Writes events to a local file in one of three formats:

    jsonl  — one JSON object per line (default; the standard format
             for streaming-friendly text data)
    csv    — comma-separated, header included
    json   — single JSON array containing all events
"""
from __future__ import annotations

import csv
import json
import logging
import os
from typing import IO, List, Optional

from ...reader.models import StormEvent
from ..interfaces import IOutputStrategy

logger = logging.getLogger(__name__)


class FileOutputStrategy(IOutputStrategy):
    name = "file"

    def __init__(self, path: str, fmt: str = "jsonl") -> None:
        self._path = path
        self._format = fmt
        self._fh: Optional[IO] = None
        self._csv_writer: Optional[csv.DictWriter] = None
        self._buffer: List[dict] = []   # only used for json (array) format

    def open(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        self._fh = open(self._path, "w", encoding="utf-8", newline="")
        logger.info("Opened %s for writing (format=%s)", self._path, self._format)

    def write(self, event: StormEvent) -> None:
        d = event.to_dict()
        if self._format == "jsonl":
            self._fh.write(json.dumps(d, ensure_ascii=False) + "\n")
        elif self._format == "csv":
            if self._csv_writer is None:
                self._csv_writer = csv.DictWriter(self._fh, fieldnames=d.keys())
                self._csv_writer.writeheader()
            self._csv_writer.writerow(d)
        elif self._format == "json":
            self._buffer.append(d)
        else:
            raise ValueError(f"Unknown file format: {self._format!r}")

    def close(self) -> None:
        if self._format == "json" and self._fh is not None:
            json.dump(self._buffer, self._fh, ensure_ascii=False, indent=2)
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        logger.info("Closed %s", self._path)
