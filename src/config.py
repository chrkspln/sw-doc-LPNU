"""
Config loader.

Reads `config.yaml` from disk and returns a plain dict.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    logger.info("Loaded config from %s: strategy=%s", path,
                (cfg or {}).get("output", {}).get("strategy"))
    return cfg or {}
