"""
Application entry point — the *Client* in the Strategy pattern.

Loads `config.yaml`, asks the factory for an `IOutputStrategy`, and
hands the reader's iterator to it. The client never knows which concrete
strategy is plugged in.

Two input modes are supported through `input.mode` in config.yaml:

    csv    — read NCDC Storm Events CSV file (the original lab use case)
    event  — read one JSON event from stdin (the Lab 3 audit-log use case)

Both modes share the same output side, so the same five strategies
(file / console / kafka / redis / firestore) work for either.

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
from .reader.event_reader import StdinEventReader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lab 4 — Strategy pattern."
    )
    parser.add_argument("--config", "-c", default="config.yaml",
                        help="Path to the config file (default: config.yaml)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    cfg = load_config(args.config)
    input_cfg = cfg.get("input") or {}
    mode = (input_cfg.get("mode") or "csv").lower().strip()

    if mode == "csv":
        path = input_cfg.get("file")
        if not path:
            print("config.yaml: input.file is required for mode=csv",
                  file=sys.stderr)
            return 2
        reader = CsvStormEventReader(path)
    elif mode == "event":
        reader = StdinEventReader()
    else:
        print(f"config.yaml: unknown input.mode {mode!r} "
              f"(expected csv or event)", file=sys.stderr)
        return 2

    strategy = build_output_strategy(cfg.get("output") or {})

    print(f"→ mode: {mode}, strategy: {strategy.name}", file=sys.stderr)
    written = strategy.write_all(reader.read())
    print(f"✓ Wrote {written} record(s) via the {strategy.name} strategy.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
