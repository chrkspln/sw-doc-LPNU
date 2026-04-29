"""
Application entry point.

This module is the *Client* in the Strategy pattern: it holds a reference
of the abstract type `IOutputStrategy` and never knows which concrete
strategy is plugged in. The decision is made inside the factory based
on `config.yaml`.

What this file does, end-to-end:

    1. Load config.yaml.
    2. Instantiate a CSV reader pointed at the configured input file.
    3. Ask the factory for an `IOutputStrategy` based on config.
    4. Hand the reader's iterator to `strategy.write_all(...)`.
    5. Log the count and exit.

Notice what it does *not* do:
    - It does not import any concrete output class.
    - It does not parse the storm-event records itself.
    - It does not know whether the destination is console, file,
      Kafka or Redis.

These three "does nots" are exactly the GoF Strategy pattern's payoff:
adding a new sink, or swapping the active one, never touches this file.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config
from .output.factory import build_output_strategy
from .reader.csv_reader import CsvStormEventReader


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lab 4 — Strategy pattern demo over the NCDC Storm Events dataset."
    )
    parser.add_argument(
        "--config", "-c", default="config.yaml",
        help="Path to the config file (default: config.yaml)",
    )
    parser.add_argument(
        "--input", "-i", default=None,
        help="Override input.file from the config (handy for ad-hoc runs).",
    )
    parser.add_argument(
        "--strategy", "-s", default=None,
        help="Override output.strategy from the config "
             "(console | file | kafka | redis).",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    cfg = load_config(args.config)
    input_file = args.input or cfg.get("input", {}).get("file", "data/storm_events.csv")
    limit = cfg.get("input", {}).get("limit")

    if not Path(input_file).exists():
        print(f"Input file not found: {input_file}", file=sys.stderr)
        print("Generate sample data with:  "
              "python -m scripts.generate_sample --output data/storm_events.csv",
              file=sys.stderr)
        return 2

    output_cfg = dict(cfg.get("output") or {})
    if args.strategy:
        output_cfg["strategy"] = args.strategy

    # 1. The reader. Only knows how to read.
    reader = CsvStormEventReader(input_file, limit=limit)

    # 2. The strategy. Only knows how to write.
    strategy = build_output_strategy(output_cfg)

    # 3. The client wires them together — neither side knows about the other.
    print(f"→ strategy: {strategy.name}  "
          f"(dry_run={output_cfg.get('dry_run', False)})",
          file=sys.stderr)

    written = strategy.write_all(reader.read())

    print(f"✓ Wrote {written} events via the {strategy.name} strategy.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
