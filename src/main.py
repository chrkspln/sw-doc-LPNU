"""
Application entry point.

Two subcommands:

    python -m src.main import --csv data/project_data.csv --clear
    python -m src.main web    --port 5000

`import` runs the Lab-2 CSV-to-DB pipeline.
`web` launches the Lab-3 Flask MVC web app.
"""
from __future__ import annotations

import argparse
import logging
import sys

from .dal.database import create_engine_and_session
from .dal.models import Base
from .di.container import Container
from .presentation.app import create_app


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _clear_database(db_url: str) -> None:
    engine, _ = create_engine_and_session(db_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def cmd_import(args: argparse.Namespace) -> int:
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


def cmd_web(args: argparse.Namespace) -> int:
    container = Container(db_url=args.db)
    app = create_app(container)
    print(f"Starting web server at http://{args.host}:{args.port}")
    print(f"Database: {args.db}")
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="Project Planning System — Lab 2 + Lab 3 entry point."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_imp = sub.add_parser("import", help="Load CSV data into the database (Lab 2 pipeline).")
    p_imp.add_argument("--csv", default="data/project_data.csv")
    p_imp.add_argument("--db", default="sqlite:///project_planning.db")
    p_imp.add_argument("--clear", action="store_true",
                       help="Drop and recreate all tables before import.")
    p_imp.set_defaults(func=cmd_import)

    p_web = sub.add_parser("web", help="Launch the Flask MVC web application (Lab 3).")
    p_web.add_argument("--host", default="127.0.0.1")
    p_web.add_argument("--port", type=int, default=5000)
    p_web.add_argument("--db", default="sqlite:///project_planning.db")
    p_web.add_argument("--debug", action="store_true")
    p_web.set_defaults(func=cmd_web)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
