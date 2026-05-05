"""
Console output strategy.

Prints each record as a JSON line to standard output.
"""
from __future__ import annotations

import json
import sys

from ..interfaces import IOutputStrategy


class ConsoleOutputStrategy(IOutputStrategy):
    name = "console"

    def open(self) -> None:
        pass

    def write(self, record) -> None:
        print(json.dumps(record.to_dict(), ensure_ascii=False))

    def close(self) -> None:
        sys.stdout.flush()
