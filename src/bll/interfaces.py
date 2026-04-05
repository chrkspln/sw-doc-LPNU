"""
BLL — service interfaces.

These are the abstractions that the Controllers (presentation layer) depend on.
Concrete implementations live in services.py and are wired in di/container.py.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from .dto import (
    AssignmentDto,
    DashboardStats,
    ProjectDetailDto,
    ProjectDto,
    ResourceDto,
    TaskDto,
)


@dataclass
class ImportReport:
    """Summary of a CSV import run (used by DataImportService)."""
    projects_created: int = 0
    tasks_created: int = 0
    resources_created: int = 0
    assignments_created: int = 0
    dependencies_created: int = 0
    calendars_created: int = 0
    baselines_created: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)

    def total_created(self) -> int:
        return (
            self.projects_created
            + self.tasks_created
            + self.resources_created
            + self.assignments_created
            + self.dependencies_created
            + self.calendars_created
            + self.baselines_created
        )

    def __str__(self) -> str:
        return (
            f"ImportReport(projects={self.projects_created}, "
            f"tasks={self.tasks_created}, resources={self.resources_created}, "
            f"assignments={self.assignments_created}, "
            f"dependencies={self.dependencies_created}, "
            f"calendars={self.calendars_created}, baselines={self.baselines_created}, "
            f"skipped={self.skipped}, errors={len(self.errors)})"
        )


# --------------------------------------------------------------------------- #
# Service contracts                                                           #
# --------------------------------------------------------------------------- #
class IDataImportService(ABC):
    """Loads project-planning data from a CSV file into the database."""

    @abstractmethod
    def import_from_csv(self, path: str) -> ImportReport: ...


class IProjectService(ABC):
    """Read/write operations on the Project aggregate (the main entity)."""

    @abstractmethod
    def list_projects(self, search: Optional[str] = None,
                      status: Optional[str] = None) -> List[ProjectDto]: ...

    @abstractmethod
    def get_project_detail(self, project_id: int) -> Optional[ProjectDetailDto]: ...

    @abstractmethod
    def create_project(self, name: str, description: Optional[str],
                       start_date, end_date=None, status: str = "PLANNED") -> ProjectDto: ...

    @abstractmethod
    def update_project(self, project_id: int, name: str, description: Optional[str],
                       start_date, end_date=None, status: str = "PLANNED") -> Optional[ProjectDto]: ...

    @abstractmethod
    def delete_project(self, project_id: int) -> bool: ...


class ITaskService(ABC):
    """Read/write operations on Tasks (and their subtypes)."""

    @abstractmethod
    def list_tasks_for_project(self, project_id: int) -> List[TaskDto]: ...

    @abstractmethod
    def get_task(self, task_id: int) -> Optional[TaskDto]: ...

    @abstractmethod
    def create_task(self, project_id: int, name: str, task_type: str,
                    duration: int, work: int, priority: int,
                    status: str, is_critical: bool,
                    parent_id: Optional[int] = None) -> TaskDto: ...

    @abstractmethod
    def update_task(self, task_id: int, name: str, duration: int, work: int,
                    priority: int, status: str, is_critical: bool,
                    percent_complete: float) -> Optional[TaskDto]: ...

    @abstractmethod
    def delete_task(self, task_id: int) -> bool: ...


class IResourceService(ABC):
    """Read-only views over Resources (org-wide pool)."""

    @abstractmethod
    def list_resources(self) -> List[ResourceDto]: ...

    @abstractmethod
    def get_resource(self, resource_id: int) -> Optional[ResourceDto]: ...


class IStatsService(ABC):
    """High-level aggregate metrics for the home/dashboard page."""

    @abstractmethod
    def get_dashboard_stats(self) -> DashboardStats: ...
