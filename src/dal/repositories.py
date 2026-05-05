"""
DAL — concrete repository implementations backed by SQLAlchemy.

All concrete repositories share the same machinery (add / get / list / delete),
so a generic base class `SqlAlchemyRepository` does the heavy lifting and
each concrete repo just declares its `model` attribute.
"""
from __future__ import annotations

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from .interfaces import (
    IAssignmentRepository,
    IBaselineRepository,
    ICalendarRepository,
    IDependencyRepository,
    IProjectRepository,
    IResourceRepository,
    ITaskRepository,
)
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


class SqlAlchemyRepository(Generic[T]):
    """
    Generic repository — every concrete subclass just sets `model`.

    Note: this class does NOT subclass IRepository directly; the concrete
    subclasses below do (they inherit from this AND from the matching
    interface). This is the standard "implementation + interface" combo.
    """

    model: Type[T]

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: T) -> T:
        self._session.add(entity)
        # flush — assigns primary key without committing the transaction
        self._session.flush()
        return entity

    def get(self, entity_id: int) -> Optional[T]:
        return self._session.get(self.model, entity_id)

    def get_by_ext_id(self, ext_id: str) -> Optional[T]:
        if ext_id is None or not hasattr(self.model, "ext_id"):
            return None
        stmt = select(self.model).where(self.model.ext_id == ext_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> List[T]:
        return list(self._session.execute(select(self.model)).scalars().all())

    def delete(self, entity_id: int) -> None:
        entity = self.get(entity_id)
        if entity is not None:
            self._session.delete(entity)


# --------------------------------------------------------------------------- #
# Concrete repositories                                                       #
# --------------------------------------------------------------------------- #
class ProjectRepository(SqlAlchemyRepository[Project], IProjectRepository):
    model = Project


class TaskRepository(SqlAlchemyRepository[Task], ITaskRepository):
    model = Task


class ResourceRepository(SqlAlchemyRepository[Resource], IResourceRepository):
    model = Resource


class AssignmentRepository(SqlAlchemyRepository[Assignment], IAssignmentRepository):
    model = Assignment

    def get_by_ext_id(self, ext_id: str) -> Optional[Assignment]:
        # Assignments are not addressed by ext_id from outside.
        return None


class DependencyRepository(SqlAlchemyRepository[Dependency], IDependencyRepository):
    model = Dependency

    def get_by_ext_id(self, ext_id: str) -> Optional[Dependency]:
        return None


class CalendarRepository(SqlAlchemyRepository[Calendar], ICalendarRepository):
    model = Calendar

    def get_by_ext_id(self, ext_id: str) -> Optional[Calendar]:
        return None


class BaselineRepository(SqlAlchemyRepository[Baseline], IBaselineRepository):
    model = Baseline

    def get_by_ext_id(self, ext_id: str) -> Optional[Baseline]:
        return None
