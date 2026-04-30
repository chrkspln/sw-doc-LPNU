"""
Kafka output strategy.

Publishes each event as a JSON message to a Kafka topic, keyed by event_id
so records for the same event are routed to the same partition. Requires
a running Kafka broker on the configured `bootstrap_servers`.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List

from ...reader.models import StormEvent
from ..interfaces import IOutputStrategy

logger = logging.getLogger(__name__)


class KafkaOutputStrategy(IOutputStrategy):
    name = "kafka"

    def __init__(self, bootstrap_servers: List[str], topic: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._producer: Any = None

    def open(self) -> None:
        try:
            from kafka import KafkaProducer
        except ImportError as e:
            raise RuntimeError(
                "kafka-python-ng is not installed. "
                "Run: pip install kafka-python-ng"
            ) from e

        logger.info("Connecting to Kafka %s, topic=%s",
                    self._bootstrap_servers, self._topic)
        self._producer = KafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

    def write(self, event: StormEvent) -> None:
        payload = event.to_dict()
        self._producer.send(self._topic, key=event.event_id, value=payload)

    def close(self) -> None:
        if self._producer is not None:
            self._producer.flush(timeout=10)
            self._producer.close(timeout=5)
            self._producer = None
