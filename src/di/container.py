"""
Dependency Injection — composition root.

This is the *only* place where the application stitches concrete classes
together. Every other module imports interfaces and receives concrete
instances through its constructor (constructor injection).

Why is this the "composition root"?
    Because changing any wiring decision — swapping SQLite for Postgres,
    the CSV reader for a JSON reader, or `DataImportService` for a
    different orchestration strategy — only affects this one file.

This Container uses simple manual DI rather than a third-party DI library.
That is intentional: the patterns (Inversion of Control, Dependency
Injection) are easier to see when no framework magic is hiding them.
"""
from __future__ import annotations

from ..bll.interfaces import IDataImportService
from ..bll.services import DataImportService
from ..dal.csv_reader import CsvDataReader
from ..dal.database import create_engine_and_session
from ..dal.interfaces import ICsvDataReader, IUnitOfWork
from ..dal.unit_of_work import SqlAlchemyUnitOfWork


class Container:
    """Manual dependency-injection container."""

    def __init__(self, db_url: str = "sqlite:///project_planning.db") -> None:
        # Long-lived singletons.
        self._engine, self._session_factory = create_engine_and_session(db_url)
        self._csv_reader: ICsvDataReader = CsvDataReader()

    # -- Factories ---------------------------------------------------------- #
    def csv_reader(self) -> ICsvDataReader:
        return self._csv_reader

    def unit_of_work(self) -> IUnitOfWork:
        # Each call returns a fresh UoW around a fresh session.
        return SqlAlchemyUnitOfWork(self._session_factory)

    def data_import_service(self) -> IDataImportService:
        # Constructor injection: BLL gets DAL abstractions, never concretes.
        return DataImportService(
            csv_reader=self.csv_reader(),
            uow=self.unit_of_work(),
        )
