"""
Presentation layer — interfaces only.

Describes what controllers/views *would* do in a future iteration;
they are not instantiated anywhere.

"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class IProjectView(ABC):
    """Renders Project data to the user."""

    @abstractmethod
    def display_project_list(self, projects: List[dict]) -> None: ...

    @abstractmethod
    def display_project_details(self, project: dict) -> None: ...


class ITaskView(ABC):
    @abstractmethod
    def display_task_list(self, tasks: List[dict]) -> None: ...


class IImportView(ABC):
    @abstractmethod
    def display_import_report(self, report) -> None: ...


# --------------------------------------------------------------------------- #
# Controllers                                                                 #
# --------------------------------------------------------------------------- #
class IProjectController(ABC):
    @abstractmethod
    def show_all_projects(self) -> None: ...

    @abstractmethod
    def show_project(self, project_id: int) -> None: ...


class ITaskController(ABC):
    @abstractmethod
    def show_tasks_for_project(self, project_id: int) -> None: ...


class IImportController(ABC):
    @abstractmethod
    def import_csv(self, path: str) -> None: ...
