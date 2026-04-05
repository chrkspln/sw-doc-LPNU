"""
Dependency Injection — composition root.

The single place in the application where concrete classes meet their
abstractions. Everything else only touches interfaces.

Services receive a `uow_factory` callable rather than a single UoW
instance. Each method invocation opens a fresh UoW (and therefore a
fresh DB session), which is the right scope for a Flask request handler
or a one-shot CLI command.
"""
from __future__ import annotations

from ..bll.interfaces import (
    IDataImportService,
    IProjectService,
    IResourceService,
    IStatsService,
    ITaskService,
)
from ..bll.services import (
    DataImportService,
    ProjectService,
    ResourceService,
    StatsService,
    TaskService,
)
from ..dal.csv_reader import CsvDataReader
from ..dal.database import create_engine_and_session
from ..dal.interfaces import ICsvDataReader, IUnitOfWork
from ..dal.unit_of_work import SqlAlchemyUnitOfWork


class Container:
    """Manual DI container. """

    def __init__(self, db_url: str = "sqlite:///project_planning.db") -> None:
        # Long-lived singletons.
        self._engine, self._session_factory = create_engine_and_session(db_url)
        self._csv_reader: ICsvDataReader = CsvDataReader()

    # ---- DAL primitives -------------------------------------------------- #
    def csv_reader(self) -> ICsvDataReader:
        return self._csv_reader

    def unit_of_work(self) -> IUnitOfWork:
        """Returns a fresh UoW around a fresh session."""
        return SqlAlchemyUnitOfWork(self._session_factory)

    # ---- BLL services ---------------------------------------------------- #
    def data_import_service(self) -> IDataImportService:
        return DataImportService(
            csv_reader=self.csv_reader(),
            uow_factory=self.unit_of_work,
        )

    def project_service(self) -> IProjectService:
        return ProjectService(uow_factory=self.unit_of_work)

    def task_service(self) -> ITaskService:
        return TaskService(uow_factory=self.unit_of_work)

    def resource_service(self) -> IResourceService:
        return ResourceService(uow_factory=self.unit_of_work)

    def stats_service(self) -> IStatsService:
        return StatsService(uow_factory=self.unit_of_work)
