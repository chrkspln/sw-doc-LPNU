"""
BLL — Data Transfer Objects.

DTOs decouple the view layer from the ORM. Controllers and templates
work with these plain dataclasses instead of SQLAlchemy entity objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class ProjectDto:
    id: int
    ext_id: Optional[str]
    name: str
    description: Optional[str]
    start_date: date
    end_date: Optional[date]
    status: str
    task_count: int = 0
    assignment_count: int = 0


@dataclass
class TaskDto:
    id: int
    ext_id: Optional[str]
    name: str
    task_type: str            # TASK | MILESTONE | SUMMARY_TASK
    duration: int
    work: int
    start_date: Optional[date]
    end_date: Optional[date]
    percent_complete: float
    priority: int
    status: str
    is_critical: bool
    project_id: int
    parent_id: Optional[int]


@dataclass
class ResourceDto:
    id: int
    ext_id: Optional[str]
    name: str
    code: str
    resource_type: str        # HUMAN_RESOURCE | MATERIAL_RESOURCE | COST_RESOURCE
    cost_per_hour: float
    max_units: float
    # Subclass-only fields (None when not applicable)
    email: Optional[str] = None
    role: Optional[str] = None
    skills: Optional[str] = None
    unit: Optional[str] = None
    consumption_rate: Optional[float] = None
    fixed_cost: Optional[float] = None


@dataclass
class AssignmentDto:
    id: int
    task_id: int
    task_name: str
    resource_id: int
    resource_name: str
    units: float
    work: int
    actual_work: int
    cost: float


@dataclass
class ProjectDetailDto:
    project: ProjectDto
    tasks: List[TaskDto] = field(default_factory=list)
    assignments: List[AssignmentDto] = field(default_factory=list)


@dataclass
class DashboardStats:
    total_projects: int
    total_tasks: int
    total_resources: int
    total_assignments: int
    projects_by_status: dict
    tasks_by_type: dict
    resources_by_type: dict
