"""
Redis output strategy.

Publishes each event to Redis using one of three storage modes:

    list   — RPUSH each event (as JSON) to a single list key. Good for
             a simple producer/consumer queue.
    stream — XADD to a Redis Stream (Redis 5+). Best when consumers
             need history or consumer groups.
    hash   — HSET each event under "{key}:{event_id}". Best when you
             want random access by event id later.

Like the Kafka strategy this supports a `dry_run` mode so the demo
works without an actual Redis instance.
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

from ...reader.models import StormEvent
from ..interfaces import IOutputStrategy

logger = logging.getLogger(__name__)


class RedisOutputStrategy(IOutputStrategy):
    name = "redis"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        mode: str = "list",
        key: str = "storm-events",
        dry_run: bool = False,
    ) -> None:
        if mode not in ("list", "stream", "hash"):
            raise ValueError(f"Unknown redis mode: {mode!r}")
        self._host = host
        self._port = port
        self._db = db
        self._mode = mode
        self._key = key
        self._dry_run = dry_run
        self._client: Any = None    # redis.Redis when real
        self._sent = 0

    def open(self) -> None:
        if self._dry_run:
            print(f"[REDIS dry-run] would connect to "
                  f"{self._host}:{self._port}/{self._db}, "
                  f"mode={self._mode}, key={self._key!r}",
                  file=sys.stderr)
            return

        try:
            import redis
        except ImportError as e:
            raise RuntimeError(
                "redis package is not installed. Either run with "
                "`output.dry_run: true` or run `pip install redis`."
            ) from e

        logger.info("Connecting to Redis %s:%d db=%d mode=%s",
                    self._host, self._port, self._db, self._mode)
        self._client = redis.Redis(
            host=self._host, port=self._port, db=self._db,
            decode_responses=False,
        )
        # Surface connection errors at open() time, not on first write().
        self._client.ping()

    def write(self, event: StormEvent) -> None:
        payload = event.to_dict()
        body = json.dumps(payload, ensure_ascii=False)

        if self._dry_run:
            print(f"[REDIS dry-run] {self._cmd_preview(event, body)}",
                  file=sys.stderr)
            self._sent += 1
            return

        if self._mode == "list":
            self._client.rpush(self._key, body)
        elif self._mode == "stream":
            # XADD wants a flat dict of bytes. Wrap the JSON blob as one field.
            self._client.xadd(self._key, {"event": body})
        elif self._mode == "hash":
            self._client.hset(f"{self._key}:{event.event_id}",
                              mapping={"data": body})
        self._sent += 1

    def close(self) -> None:
        if self._dry_run:
            print(f"[REDIS dry-run] would have sent {self._sent} entries",
                  file=sys.stderr)
            return

        if self._client is not None:
            logger.info("Closing Redis connection (%d entries written)",
                        self._sent)
            self._client.close()
            self._client = None

    # ----- internals ------------------------------------------------------ #
    def _cmd_preview(self, event: StormEvent, body: str) -> str:
        if self._mode == "list":
            return f"RPUSH {self._key} {body}"
        if self._mode == "stream":
            return f"XADD {self._key} * event {body}"
        return f"HSET {self._key}:{event.event_id} data {body}"
