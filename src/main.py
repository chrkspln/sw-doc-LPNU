"""
Application entry point — the *Client* in the Strategy pattern.

Loads `config.yaml`, asks the factory for an `IOutputStrategy`, and
hands the reader's iterator to it. The client never knows or asks
which concrete strategy is plugged in.

To switch destinations, edit `config.yaml`. There is no CLI override
because the lab requires that swapping happens through configuration
files alone.
"""
from __future__ import annotations

import argparse
import logging
import sys

from .config import load_config
from .output.factory import build_output_strategy
from .reader.csv_reader import CsvStormEventReader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lab 4 — Strategy pattern over the NCDC Storm Events dataset."
    )
    parser.add_argument("--config", "-c", default="config.yaml",
                        help="Path to the config file (default: config.yaml)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = load_config(args.config)
    input_file = cfg.get("input", {}).get("file")
    if not input_file:
        print("config.yaml: input.file is required", file=sys.stderr)
        return 2

    reader = CsvStormEventReader(input_file)
    strategy = build_output_strategy(cfg.get("output") or {})

    print(f"→ strategy: {strategy.name}", file=sys.stderr)
    written = strategy.write_all(reader.read())
    print(f"✓ Wrote {written} events via the {strategy.name} strategy.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
