"""
DAL — abstract interfaces.

Contents:
    - Repository protocols (one per aggregate root + association tables)
    - Unit-of-Work protocol (transactional boundary spanning all repos)
    - CSV reader protocol (data-source abstraction)
    - CsvRecord — a typed-attribute view of a single CSV row
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, List, Optional, TypeVar

from .models import (
    Assignment,
    Baseline,
    Calendar,
    Dependency,
    Project,
    Resource,
    Task,
)

T = TypeVar("T")


# --------------------------------------------------------------------------- #
# Repository contracts                                                        #
# --------------------------------------------------------------------------- #
class IRepository(ABC, Generic[T]):
    """Dummies every repository implements."""

    @abstractmethod
    def add(self, entity: T) -> T: ...

    @abstractmethod
    def get(self, entity_id: int) -> Optional[T]: ...

    @abstractmethod
    def get_by_ext_id(self, ext_id: str) -> Optional[T]: ...

    @abstractmethod
    def list_all(self) -> List[T]: ...

    @abstractmethod
    def delete(self, entity_id: int) -> None: ...


class IProjectRepository(IRepository[Project]):
    """Persistence operations for Project aggregate."""


class ITaskRepository(IRepository[Task]):
    """Persistence operations for Task and its subclasses (Milestone, SummaryTask)."""


class IResourceRepository(IRepository[Resource]):
    """Persistence operations for Resource and its subclasses."""


class IAssignmentRepository(IRepository[Assignment]):
    """Persistence operations for Task <-> Resource assignments."""


class IDependencyRepository(IRepository[Dependency]):
    """Persistence operations for Task <-> Task dependencies."""


class ICalendarRepository(IRepository[Calendar]): ...


class IBaselineRepository(IRepository[Baseline]): ...


# --------------------------------------------------------------------------- #
# Unit of Work — transactional boundary                                       #
# --------------------------------------------------------------------------- #
class IUnitOfWork(ABC):
    """
    Coordinates multiple repositories under a single transaction.

    Used as a context manager:

        with uow:
            uow.projects.add(...)
            uow.tasks.add(...)
            uow.commit()
    """

    projects: IProjectRepository
    tasks: ITaskRepository
    resources: IResourceRepository
    assignments: IAssignmentRepository
    dependencies: IDependencyRepository
    calendars: ICalendarRepository
    baselines: IBaselineRepository

    @abstractmethod
    def __enter__(self) -> "IUnitOfWork": ...

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...


# --------------------------------------------------------------------------- #
# CSV reader contract                                                         #
# --------------------------------------------------------------------------- #
class CsvRecord:
    """
    A typed-attribute view of a CSV row.

    Each header column becomes an attribute on the instance. Empty
    strings are normalized to `None` by the reader.
    """

    def __init__(self, **fields: Any) -> None:
        self._fields = fields
        for k, v in fields.items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        rt = getattr(self, "record_type", "?")
        ext = getattr(self, "ext_id", "?")
        return f"<CsvRecord type={rt} ext_id={ext}>"


class ICsvDataReader(ABC):
    """Reads project-planning records from a single CSV file."""

    @abstractmethod
    def read(self, path: str) -> Iterable[CsvRecord]: ...
