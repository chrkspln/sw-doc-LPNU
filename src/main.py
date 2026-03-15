"""
Application entry point.

Usage:
    python -m src.main --csv data/project_data.csv
    python -m src.main --csv data/project_data.csv --db sqlite:///custom.db
"""
from __future__ import annotations

import argparse
import logging
import sys

from .dal.database import create_engine_and_session
from .dal.models import Base
from .di.container import Container


def _clear_database(db_url: str) -> None:
    """Drop and recreate all tables so the import can run fresh."""
    engine, _ = create_engine_and_session(db_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="Project Planning System — load CSV data into the database."
    )
    parser.add_argument(
        "--csv",
        default="data/project_data.csv",
        help="Path to the CSV input file (default: data/project_data.csv)",
    )
    parser.add_argument(
        "--db",
        default="sqlite:///project_planning.db",
        help="SQLAlchemy database URL (default: sqlite:///project_planning.db)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Drop and recreate all tables before import (useful for repeat runs).",
    )
    args = parser.parse_args(argv)

    if args.clear:
        print(f"Clearing database at {args.db}…")
        _clear_database(args.db)

    container = Container(db_url=args.db)
    importer = container.data_import_service()

    print(f"Importing data from {args.csv} → {args.db}")
    report = importer.import_from_csv(args.csv)
    print(f"Done.\n  {report}")
    print(f"  Total entities created: {report.total_created()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
