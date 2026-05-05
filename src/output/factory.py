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
from .strategies.firestore import FirestoreOutputStrategy
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

    if name == "firestore":
        cfg = output_cfg.get("firestore") or {}
        # Allow the credentials path to come from an env var (handy for
        # keeping the secret out of config.yaml in shared repos).
        creds = cfg.get("credentials_path")
        if creds and creds.startswith("$"):
            import os
            env_name = creds[1:]
            creds = os.environ.get(env_name)
            if not creds:
                raise ValueError(
                    f"firestore.credentials_path references env var "
                    f"${env_name} but it is not set."
                )
        if not creds:
            raise ValueError(
                "firestore.credentials_path is required (path to the "
                "Firebase service-account JSON file)."
            )
        return FirestoreOutputStrategy(
            credentials_path=creds,
            collection=cfg.get("collection", "events"),
        )

    raise ValueError(
        f"Unknown output.strategy {name!r}. "
        f"Expected one of: file, console, kafka, redis, firestore."
    )
