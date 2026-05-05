"""
Factory for output strategies.

The single seam through which a config string ("console" | "kafka" | "redis")
is turned into a concrete `IOutputStrategy`. The rest of the application
only sees the abstract type.
"""
from __future__ import annotations

from typing import Dict

from .interfaces import IOutputStrategy
from .strategies.console import ConsoleOutputStrategy
from .strategies.file import FileOutputStrategy
from .strategies.kafka import KafkaOutputStrategy
from .strategies.redis import RedisOutputStrategy


def build_output_strategy(output_cfg: Dict) -> IOutputStrategy:
    name = (output_cfg.get("strategy") or "file").lower().strip()

    if name == "file":
        cfg = output_cfg.get("file") or {}
        return FileOutputStrategy(path=cfg.get("path", "data/output.jsonl"))

    if name == "console":
        return ConsoleOutputStrategy()

    if name == "kafka":
        cfg = output_cfg.get("kafka") or {}
        servers = cfg.get("bootstrap_servers", ["localhost:9092"])
        if isinstance(servers, str):
            servers = [servers]
        return KafkaOutputStrategy(
            bootstrap_servers=servers,
            topic=cfg.get("topic", "storm-events"),
        )

    if name == "redis":
        cfg = output_cfg.get("redis") or {}
        return RedisOutputStrategy(
            host=cfg.get("host", "localhost"),
            port=int(cfg.get("port", 6379)),
            db=int(cfg.get("db", 0)),
            key=cfg.get("key", "storm-events"),
        )

    raise ValueError(
        f"Unknown output.strategy {name!r}. "
        f"Expected one of: file, console, kafka, redis."
    )
