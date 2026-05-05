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

import logging
from typing import Optional

from ..bll.interfaces import (
    IDataImportService,
    IEventPublisher,
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
from ..integration.lab4_publisher import Lab4SubprocessPublisher

logger = logging.getLogger(__name__)


class _NullEventPublisher(IEventPublisher):
    """No-op publisher used when Lab 4 isn't configured for this run."""

    def publish(self, action, entity_type, entity_id=None, details=None):
        logger.debug("Event ignored (no Lab 4 configured): %s on %s/%s",
                     action, entity_type, entity_id)


class Container:
    """Manual DI container — explicit wiring, no framework magic."""

    def __init__(
        self,
        db_url: str = "sqlite:///project_planning.db",
        lab4_dir: Optional[str] = None,
        lab4_config: str = "config.yaml",
        user_provider: Optional[callable] = None,
    ) -> None:
        # Long-lived singletons.
        self._engine, self._session_factory = create_engine_and_session(db_url)
        self._csv_reader: ICsvDataReader = CsvDataReader()
        self._lab4_dir = lab4_dir
        self._lab4_config = lab4_config

        # Build the publisher once; pre-import-time decision based on whether
        # the operator told us where Lab 4 lives.
        if lab4_dir:
            kwargs = {"lab4_dir": lab4_dir, "config_path": lab4_config}
            if user_provider is not None:
                kwargs["user_provider"] = user_provider
            self._event_publisher: IEventPublisher = Lab4SubprocessPublisher(**kwargs)
            logger.info("Event publisher: Lab4SubprocessPublisher (lab4_dir=%s)",
                        lab4_dir)
        else:
            self._event_publisher = _NullEventPublisher()
            logger.info("Event publisher: disabled (no LAB4_DIR configured)")

    # ---- DAL primitives -------------------------------------------------- #
    def csv_reader(self) -> ICsvDataReader:
        return self._csv_reader

    def unit_of_work(self) -> IUnitOfWork:
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

    # ---- Integration ----------------------------------------------------- #
    def event_publisher(self) -> IEventPublisher:
        return self._event_publisher
