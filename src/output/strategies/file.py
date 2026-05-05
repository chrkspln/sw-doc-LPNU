"""
File output strategy.

Writes each record as a JSON line to a local file. Opens in append mode
so that repeated invocations (e.g. Lab 3 firing one event per click)
accumulate rather than overwrite.
"""
from __future__ import annotations

import json
import logging
import os
from typing import IO, Optional

from ..interfaces import IOutputStrategy

logger = logging.getLogger(__name__)


class FileOutputStrategy(IOutputStrategy):
    name = "file"

    def __init__(self, path: str) -> None:
        self._path = path
        self._fh: Optional[IO] = None

    def open(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        self._fh = open(self._path, "a", encoding="utf-8")
        logger.info("Opened %s for append", self._path)

    def write(self, record) -> None:
        self._fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        logger.info("Closed %s", self._path)
