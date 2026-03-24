"""
Dependency Injection — composition root.

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
        # Constructor injection: BLL gets DAL abstractions.
        return DataImportService(
            csv_reader=self.csv_reader(),
            uow=self.unit_of_work(),
        )
