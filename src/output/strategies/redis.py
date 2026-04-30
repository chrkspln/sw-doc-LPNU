"""
Redis output strategy.

Publishes each event as a JSON string to a Redis list (`RPUSH`).
Requires a running Redis server on the configured host:port.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ...reader.models import StormEvent
from ..interfaces import IOutputStrategy

logger = logging.getLogger(__name__)


class RedisOutputStrategy(IOutputStrategy):
    name = "redis"

    def __init__(self, host: str, port: int, db: int, key: str) -> None:
        self._host = host
        self._port = port
        self._db = db
        self._key = key
        self._client: Any = None

    def open(self) -> None:
        try:
            import redis
        except ImportError as e:
            raise RuntimeError(
                "redis is not installed. Run: pip install redis"
            ) from e

        logger.info("Connecting to Redis %s:%d db=%d",
                    self._host, self._port, self._db)
        self._client = redis.Redis(host=self._host, port=self._port,
                                   db=self._db, decode_responses=False)
        self._client.ping()

    def write(self, event: StormEvent) -> None:
        payload = event.to_dict()
        self._client.rpush(self._key, json.dumps(payload, ensure_ascii=False))

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
