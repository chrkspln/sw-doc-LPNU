"""
BLL — service interfaces.

"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class ImportReport:
    """Summary of a CSV import run."""
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


class IDataImportService(ABC):
    """Top-level use case: load project-planning data from CSV into the DB."""

    @abstractmethod
    def import_from_csv(self, path: str) -> ImportReport: ...
