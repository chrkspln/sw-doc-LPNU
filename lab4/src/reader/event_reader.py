"""
Event reader — reads one JSON event from stdin.

Used when Lab 3 invokes Lab 4 as a subprocess to log a single CRUD action.
The caller pipes JSON to Lab 4's stdin, the reader parses it into an
`Event`, and the configured strategy ships it to Firestore (or wherever
the config points).

Designed for one-shot use — Lab 3 spawns one Lab 4 process per click.
"""
from __future__ import annotations

import json
import sys
from typing import Iterator

from .event import Event
from .interfaces import IEventReader


class StdinEventReader(IEventReader):
    def read(self) -> Iterator[Event]:
        raw = sys.stdin.read().strip()
        if not raw:
            return
        payload = json.loads(raw)
        yield Event(
            timestamp=payload["timestamp"],
            action=payload["action"],
            entity_type=payload["entity_type"],
            entity_id=payload.get("entity_id"),
            user=payload.get("user", "anonymous"),
            details=payload.get("details", {}),
        )
