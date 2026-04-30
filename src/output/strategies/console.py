"""
Console output strategy.

Prints each event as a JSON line to standard output.
"""
from __future__ import annotations

import json
import sys

from ...reader.models import StormEvent
from ..interfaces import IOutputStrategy


class ConsoleOutputStrategy(IOutputStrategy):
    name = "console"

    def open(self) -> None:
        pass

    def write(self, event: StormEvent) -> None:
        print(json.dumps(event.to_dict(), ensure_ascii=False))

    def close(self) -> None:
        sys.stdout.flush()
