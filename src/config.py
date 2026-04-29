"""
Config loader.

Reads `config.yaml` from disk and returns a plain dict. PyYAML is the
only YAML dependency; if it isn't installed, we fall back to a tiny
JSON loader so the project still runs in environments where YAML
isn't available.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if path.lower().endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError as e:
            raise RuntimeError(
                "PyYAML is required for YAML config files. "
                "Install it with `pip install PyYAML`, or provide "
                "a JSON config instead."
            ) from e
        cfg = yaml.safe_load(text)
    else:
        cfg = json.loads(text)

    logger.info("Loaded config from %s: strategy=%s dry_run=%s",
                path,
                cfg.get("output", {}).get("strategy"),
                cfg.get("output", {}).get("dry_run"))
    return cfg or {}
