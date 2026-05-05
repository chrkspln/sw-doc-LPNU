"""
DAL — database setup.

Builds the SQLAlchemy `Engine` and a `sessionmaker`. The engine is the
DB-level connection pool; the sessionmaker hands out `Session` objects
that the Unit of Work owns.

The schema is created from the ORM metadata on first run.
"""
from __future__ import annotations

from typing import Tuple

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


def create_engine_and_session(
    db_url: str = "sqlite:///project_planning.db",
    echo: bool = False,
) -> Tuple[Engine, sessionmaker]:
    engine = create_engine(db_url, echo=echo, future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory
