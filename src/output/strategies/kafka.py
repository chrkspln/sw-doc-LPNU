"""
Kafka output strategy.

Publishes each event as a JSON message to a Kafka topic. The message
key is a configurable field of the event (defaults to ``event_id``) so
records for the same event are routed to the same partition.

Two modes:
    - real:     opens a `KafkaProducer` against ``bootstrap_servers``
                and sends every event. Requires a running Kafka broker
                (a `docker-compose.yml` in the project root brings one up).
    - dry-run:  prints `[KAFKA dry-run]` lines showing exactly what
                *would* be sent. Useful for demonstrating the Strategy
                pattern when no broker is available.

`kafka-python` is imported lazily so that running the program with the
console strategy never requires the kafka library to be installed.
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any, List, Optional

from ...reader.models import StormEvent
from ..interfaces import IOutputStrategy

logger = logging.getLogger(__name__)


class KafkaOutputStrategy(IOutputStrategy):
    name = "kafka"

    def __init__(
        self,
        bootstrap_servers: List[str],
        topic: str,
        key_field: str = "event_id",
        acks: int = 1,
        client_id: str = "lab4-producer",
        dry_run: bool = False,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._key_field = key_field
        self._acks = acks
        self._client_id = client_id
        self._dry_run = dry_run
        self._producer: Any = None    # KafkaProducer when real
        self._sent = 0

    def open(self) -> None:
        if self._dry_run:
            print(f"[KAFKA dry-run] would connect to "
                  f"{self._bootstrap_servers}, topic={self._topic!r}",
                  file=sys.stderr)
            return

        try:
            from kafka import KafkaProducer
        except ImportError as e:
            raise RuntimeError(
                "kafka-python-ng is not installed. Either run with "
                "`output.dry_run: true` or run `pip install kafka-python-ng`."
            ) from e

        logger.info("Connecting to Kafka %s, topic=%s",
                    self._bootstrap_servers, self._topic)
        self._producer = KafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
            acks=self._acks,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

    def write(self, event: StormEvent) -> None:
        payload = event.to_dict()
        key: Optional[str] = str(payload.get(self._key_field) or event.event_id)

        if self._dry_run:
            print(f"[KAFKA dry-run] → topic={self._topic} "
                  f"key={key} payload={json.dumps(payload, ensure_ascii=False)}",
                  file=sys.stderr)
            self._sent += 1
            return

        future = self._producer.send(self._topic, key=key, value=payload)
        # Optional: block on the per-record future to surface broker errors
        # immediately. We don't here — we rely on `flush()` in close() — but
        # we keep the future to satisfy linters and document the intent.
        del future
        self._sent += 1

    def close(self) -> None:
        if self._dry_run:
            print(f"[KAFKA dry-run] would have sent {self._sent} messages",
                  file=sys.stderr)
            return

        if self._producer is not None:
            logger.info("Flushing Kafka producer (%d messages buffered)",
                        self._sent)
            self._producer.flush(timeout=10)
            self._producer.close(timeout=5)
            self._producer = None
