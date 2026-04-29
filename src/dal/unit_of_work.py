"""
DAL — Unit of Work implementation.

Wraps a SQLAlchemy session and exposes one repository per aggregate.
Used as a context manager to ensure the 'open session → use repos →
commit or rollback → close session' lifecycle.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from .interfaces import IUnitOfWork
from .repositories import (
    AssignmentRepository,
    BaselineRepository,
    CalendarRepository,
    DependencyRepository,
    ProjectRepository,
    ResourceRepository,
    TaskRepository,
)


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory
        self._session: Optional[Session] = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        # Wire repositories around the active session.
        self.projects = ProjectRepository(self._session)
        self.tasks = TaskRepository(self._session)
        self.resources = ResourceRepository(self._session)
        self.assignments = AssignmentRepository(self._session)
        self.dependencies = DependencyRepository(self._session)
        self.calendars = CalendarRepository(self._session)
        self.baselines = BaselineRepository(self._session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            if self._session is not None:
                self._session.close()
                self._session = None

    def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active — use it as a context manager.")
        self._session.commit()

    def rollback(self) -> None:
        if self._session is None:
            return
        self._session.rollback()
