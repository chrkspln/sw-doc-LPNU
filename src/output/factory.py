"""
Factory for output strategies.

The factory is the single seam through which a config string
(``"console"`` / ``"file"`` / ``"kafka"`` / ``"redis"``) is turned into
a concrete `IOutputStrategy` instance. The rest of the application only
ever sees the abstract type.

Adding a fifth sink later (S3, PostgreSQL, RabbitMQ…) means writing
one new strategy class and adding one branch here. No other code
changes are required — that's the open/closed principle in action.
"""
from __future__ import annotations

from typing import Dict

from .interfaces import IOutputStrategy
from .strategies.console import ConsoleOutputStrategy
from .strategies.file import FileOutputStrategy
from .strategies.kafka import KafkaOutputStrategy
from .strategies.redis import RedisOutputStrategy


def build_output_strategy(output_cfg: Dict) -> IOutputStrategy:
    """Build the configured strategy.

    `output_cfg` is the parsed `output:` section of `config.yaml`.
    """
    name = (output_cfg.get("strategy") or "console").lower().strip()
    dry_run = bool(output_cfg.get("dry_run", False))

    if name == "console":
        cfg = output_cfg.get("console") or {}
        return ConsoleOutputStrategy(
            fmt=cfg.get("format", "pretty"),
            color=bool(cfg.get("color", True)),
        )

    if name == "file":
        cfg = output_cfg.get("file") or {}
        return FileOutputStrategy(
            path=cfg.get("path", "data/output.jsonl"),
            fmt=cfg.get("format", "jsonl"),
        )

    if name == "kafka":
        cfg = output_cfg.get("kafka") or {}
        servers = cfg.get("bootstrap_servers", ["localhost:9092"])
        if isinstance(servers, str):
            servers = [servers]
        return KafkaOutputStrategy(
            bootstrap_servers=servers,
            topic=cfg.get("topic", "storm-events"),
            key_field=cfg.get("key_field", "event_id"),
            acks=int(cfg.get("acks", 1)),
            client_id=cfg.get("client_id", "lab4-producer"),
            dry_run=dry_run,
        )

    if name == "redis":
        cfg = output_cfg.get("redis") or {}
        return RedisOutputStrategy(
            host=cfg.get("host", "localhost"),
            port=int(cfg.get("port", 6379)),
            db=int(cfg.get("db", 0)),
            mode=cfg.get("mode", "list"),
            key=cfg.get("key", "storm-events"),
            dry_run=dry_run,
        )

    raise ValueError(
        f"Unknown output.strategy {name!r}. "
        f"Expected one of: console, file, kafka, redis."
    )
