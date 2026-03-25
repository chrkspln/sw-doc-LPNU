"""
Presentation layer — interfaces only.

The lab specifies that the presentation layer currently performs no logic
and is represented purely by interfaces. These interfaces describe what
controllers/views *would* do in a future iteration; they are not
instantiated anywhere in this lab.

A typical web/desktop UI implementation would inject the BLL services
(via the same DI container that wires the rest of the app) and translate
HTTP requests / button clicks into service calls.
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
# Controllers (would coordinate views + BLL services in a real UI)            #
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
