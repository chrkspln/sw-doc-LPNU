"""
BLL — service implementations.

All services depend on a `uow_factory` (a callable returning a fresh
`IUnitOfWork`) instead of a single UoW instance. This keeps services
stateless and thread-safe — each public method opens its own UoW
context, performs its work, and either commits or rolls back.

Concrete services in this module:
    - DataImportService  (CSV → DB ETL, used by CLI)
    - ProjectService     (Project CRUD + listing)
    - TaskService        (Task CRUD inside a project)
    - ResourceService    (read-only Resource access)
    - StatsService       (aggregate metrics for the dashboard)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Callable, Dict, Iterable, List, Optional

from ..dal.interfaces import CsvRecord, ICsvDataReader, IUnitOfWork
from ..dal.models import (
    Assignment,
    Baseline,
    Calendar,
    CostResource,
    Dependency,
    HumanResource,
    MaterialResource,
    Milestone,
    Project,
    Resource,
    SummaryTask,
    Task,
)
from .dto import (
    AssignmentDto,
    DashboardStats,
    ProjectDetailDto,
    ProjectDto,
    ResourceDto,
    TaskDto,
)
from .interfaces import (
    IDataImportService,
    ImportReport,
    IProjectService,
    IResourceService,
    IStatsService,
    ITaskService,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Parsing helpers                                                             #
# --------------------------------------------------------------------------- #
def _parse_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_int(value, default: int = 0) -> int:
    if value is None or value == "":
        return default
    return int(float(value))


def _parse_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _parse_bool(value) -> bool:
    if value is None or value == "":
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def _attr(record: CsvRecord, name: str):
    return getattr(record, name, None)


# --------------------------------------------------------------------------- #
# DTO mapping helpers                                                         #
# --------------------------------------------------------------------------- #
def _to_project_dto(p: Project, task_count: int = 0, assignment_count: int = 0) -> ProjectDto:
    return ProjectDto(
        id=p.id,
        ext_id=p.ext_id,
        name=p.name,
        description=p.description,
        start_date=p.start_date,
        end_date=p.end_date,
        status=p.status,
        task_count=task_count,
        assignment_count=assignment_count,
    )


def _to_task_dto(t: Task) -> TaskDto:
    return TaskDto(
        id=t.id,
        ext_id=t.ext_id,
        name=t.name,
        task_type=t.task_type,
        duration=t.duration,
        work=t.work,
        start_date=t.start_date,
        end_date=t.end_date,
        percent_complete=t.percent_complete,
        priority=t.priority,
        status=t.status,
        is_critical=t.is_critical,
        project_id=t.project_id,
        parent_id=t.parent_id,
    )


def _to_resource_dto(r: Resource) -> ResourceDto:
    return ResourceDto(
        id=r.id,
        ext_id=r.ext_id,
        name=r.name,
        code=r.code,
        resource_type=r.resource_type,
        cost_per_hour=r.cost_per_hour,
        max_units=r.max_units,
        email=r.email,
        role=r.role,
        skills=r.skills,
        unit=r.unit,
        consumption_rate=r.consumption_rate,
        fixed_cost=r.fixed_cost,
    )


# --------------------------------------------------------------------------- #
# DataImportService — CSV → DB                                                #
# --------------------------------------------------------------------------- #
class DataImportService(IDataImportService):
    def __init__(
        self,
        csv_reader: ICsvDataReader,
        uow_factory: Callable[[], IUnitOfWork],
    ) -> None:
        self._csv_reader = csv_reader
        self._uow_factory = uow_factory

    def import_from_csv(self, path: str) -> ImportReport:
        report = ImportReport()
        records: List[CsvRecord] = list(self._csv_reader.read(path))
        logger.info("Read %d records from %s", len(records), path)

        grouped: Dict[str, List[CsvRecord]] = defaultdict(list)
        for r in records:
            rt = _attr(r, "record_type")
            if rt:
                grouped[rt].append(r)

        project_ids: Dict[str, int] = {}
        task_ids: Dict[str, int] = {}
        resource_ids: Dict[str, int] = {}

        with self._uow_factory() as uow:
            try:
                self._import_projects(grouped["PROJECT"], uow, project_ids, report)
                self._import_calendars(grouped["CALENDAR"], uow, project_ids, report)
                self._import_baselines(grouped["BASELINE"], uow, project_ids, report)
                self._import_resources(
                    grouped["HUMAN_RESOURCE"]
                    + grouped["MATERIAL_RESOURCE"]
                    + grouped["COST_RESOURCE"],
                    uow, resource_ids, report,
                )
                self._import_tasks(grouped["SUMMARY_TASK"], uow, project_ids, task_ids, report)
                self._import_tasks(grouped["TASK"], uow, project_ids, task_ids, report)
                self._import_tasks(grouped["MILESTONE"], uow, project_ids, task_ids, report)
                self._import_dependencies(grouped["DEPENDENCY"], uow, task_ids, report)
                self._import_assignments(grouped["ASSIGNMENT"], uow, task_ids, resource_ids, report)
                uow.commit()
                logger.info("Import committed: %s", report)
            except Exception as exc:
                logger.exception("Import failed; rolling back")
                report.errors.append(str(exc))
                raise

        return report

    def _import_projects(self, rows, uow, project_ids, report):
        for r in rows:
            p = Project(
                ext_id=_attr(r, "ext_id"),
                name=_attr(r, "name") or f"Project {_attr(r, 'ext_id')}",
                description=_attr(r, "description"),
                start_date=_parse_date(_attr(r, "start_date")) or date.today(),
                end_date=_parse_date(_attr(r, "end_date")),
                status=_attr(r, "status") or "PLANNED",
            )
            uow.projects.add(p)
            if r.ext_id:
                project_ids[r.ext_id] = p.id
            report.projects_created += 1

    def _import_calendars(self, rows, uow, project_ids, report):
        for r in rows:
            proj_id = project_ids.get(_attr(r, "project_ext_id"))
            if proj_id is None:
                report.skipped += 1
                continue
            uow.calendars.add(Calendar(
                project_id=proj_id,
                working_days=_attr(r, "working_days") or "MON;TUE;WED;THU;FRI",
                working_hours=_attr(r, "working_hours") or "09:00-18:00",
            ))
            report.calendars_created += 1

    def _import_baselines(self, rows, uow, project_ids, report):
        for r in rows:
            proj_id = project_ids.get(_attr(r, "project_ext_id"))
            if proj_id is None:
                report.skipped += 1
                continue
            uow.baselines.add(Baseline(
                project_id=proj_id,
                saved_date=_parse_date(_attr(r, "saved_date")) or date.today(),
            ))
            report.baselines_created += 1

    def _import_resources(self, rows, uow, resource_ids, report):
        for r in rows:
            common = dict(
                ext_id=_attr(r, "ext_id"),
                name=_attr(r, "name") or _attr(r, "ext_id"),
                code=_attr(r, "code") or _attr(r, "ext_id"),
                cost_per_hour=_parse_float(_attr(r, "cost_per_hour")),
                max_units=_parse_float(_attr(r, "max_units"), default=1.0),
            )
            rt = _attr(r, "record_type")
            if rt == "HUMAN_RESOURCE":
                obj = HumanResource(**common, email=_attr(r, "email"),
                                    role=_attr(r, "role"), skills=_attr(r, "skills"))
            elif rt == "MATERIAL_RESOURCE":
                obj = MaterialResource(**common, unit=_attr(r, "unit"),
                                       consumption_rate=_parse_float(_attr(r, "consumption_rate")))
            elif rt == "COST_RESOURCE":
                obj = CostResource(**common, fixed_cost=_parse_float(_attr(r, "fixed_cost")))
            else:
                report.skipped += 1
                continue
            uow.resources.add(obj)
            if r.ext_id:
                resource_ids[r.ext_id] = obj.id
            report.resources_created += 1

    def _import_tasks(self, rows, uow, project_ids, task_ids, report):
        for r in rows:
            proj_id = project_ids.get(_attr(r, "project_ext_id"))
            if proj_id is None:
                report.skipped += 1
                continue
            parent_id = task_ids.get(_attr(r, "summary_ext_id")) if _attr(r, "summary_ext_id") else None
            cls = {"TASK": Task, "MILESTONE": Milestone, "SUMMARY_TASK": SummaryTask}.get(_attr(r, "record_type"), Task)
            t = cls(
                ext_id=_attr(r, "ext_id"),
                name=_attr(r, "name") or _attr(r, "ext_id"),
                duration=_parse_int(_attr(r, "duration")),
                work=_parse_int(_attr(r, "work")),
                start_date=_parse_date(_attr(r, "start_date")),
                end_date=_parse_date(_attr(r, "end_date")),
                percent_complete=_parse_float(_attr(r, "percent_complete")),
                priority=_parse_int(_attr(r, "priority"), default=500),
                status=_attr(r, "status") or "NOT_STARTED",
                is_critical=_parse_bool(_attr(r, "is_critical")),
                project_id=proj_id,
                parent_id=parent_id,
            )
            uow.tasks.add(t)
            if r.ext_id:
                task_ids[r.ext_id] = t.id
            report.tasks_created += 1

    def _import_dependencies(self, rows, uow, task_ids, report):
        for r in rows:
            pred = task_ids.get(_attr(r, "predecessor_ext_id"))
            succ = task_ids.get(_attr(r, "successor_ext_id"))
            if pred is None or succ is None or pred == succ:
                report.skipped += 1
                continue
            uow.dependencies.add(Dependency(
                predecessor_id=pred, successor_id=succ,
                dep_type=_attr(r, "dep_type") or "FS",
                lag=_parse_int(_attr(r, "lag")),
            ))
            report.dependencies_created += 1

    def _import_assignments(self, rows, uow, task_ids, resource_ids, report):
        for r in rows:
            tid = task_ids.get(_attr(r, "task_ext_id"))
            rid = resource_ids.get(_attr(r, "resource_ext_id"))
            if tid is None or rid is None:
                report.skipped += 1
                continue
            uow.assignments.add(Assignment(
                task_id=tid, resource_id=rid,
                units=_parse_float(_attr(r, "units"), default=1.0),
                work=_parse_int(_attr(r, "work")),
                actual_work=_parse_int(_attr(r, "actual_work")),
                cost=_parse_float(_attr(r, "cost")),
            ))
            report.assignments_created += 1


# --------------------------------------------------------------------------- #
# ProjectService — main entity CRUD                                           #
# --------------------------------------------------------------------------- #
class ProjectService(IProjectService):
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def list_projects(self) -> List[ProjectDto]:
        with self._uow_factory() as uow:
            projects = uow.projects.list_all()
            results: List[ProjectDto] = []
            for p in projects:
                tasks = [t for t in p.tasks]
                assignments = sum(len(t.assignments) for t in tasks)
                results.append(_to_project_dto(p, len(tasks), assignments))
            results.sort(key=lambda d: d.name.lower())
            return results

    def get_project_detail(self, project_id: int) -> Optional[ProjectDetailDto]:
        with self._uow_factory() as uow:
            p = uow.projects.get(project_id)
            if p is None:
                return None
            tasks = [_to_task_dto(t) for t in p.tasks]
            assignments: List[AssignmentDto] = []
            for t in p.tasks:
                for a in t.assignments:
                    assignments.append(AssignmentDto(
                        id=a.id,
                        task_id=a.task_id, task_name=t.name,
                        resource_id=a.resource_id,
                        resource_name=a.resource.name if a.resource else "—",
                        units=a.units, work=a.work,
                        actual_work=a.actual_work, cost=a.cost,
                    ))
            project_dto = _to_project_dto(p, len(tasks), len(assignments))
            return ProjectDetailDto(project=project_dto, tasks=tasks, assignments=assignments)

    def create_project(self, name, description, start_date, end_date=None, status="PLANNED") -> ProjectDto:
        with self._uow_factory() as uow:
            p = Project(
                name=name,
                description=description,
                start_date=_parse_date(start_date) if isinstance(start_date, str) else (start_date or date.today()),
                end_date=_parse_date(end_date) if isinstance(end_date, str) else end_date,
                status=status,
            )
            uow.projects.add(p)
            uow.commit()
            return _to_project_dto(p)

    def update_project(self, project_id, name, description, start_date, end_date=None, status="PLANNED"):
        with self._uow_factory() as uow:
            p = uow.projects.get(project_id)
            if p is None:
                return None
            p.name = name
            p.description = description
            p.start_date = _parse_date(start_date) if isinstance(start_date, str) else start_date
            p.end_date = _parse_date(end_date) if isinstance(end_date, str) else end_date
            p.status = status
            uow.commit()
            return _to_project_dto(p)

    def delete_project(self, project_id) -> bool:
        with self._uow_factory() as uow:
            p = uow.projects.get(project_id)
            if p is None:
                return False
            uow.projects.delete(project_id)
            uow.commit()
            return True


# --------------------------------------------------------------------------- #
# TaskService — Task CRUD inside a Project                                    #
# --------------------------------------------------------------------------- #
class TaskService(ITaskService):
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def list_tasks_for_project(self, project_id) -> List[TaskDto]:
        with self._uow_factory() as uow:
            p = uow.projects.get(project_id)
            if p is None:
                return []
            tasks = sorted(p.tasks, key=lambda t: (t.task_type != "SUMMARY_TASK", t.priority, t.name))
            return [_to_task_dto(t) for t in tasks]

    def get_task(self, task_id) -> Optional[TaskDto]:
        with self._uow_factory() as uow:
            t = uow.tasks.get(task_id)
            return _to_task_dto(t) if t else None

    def create_task(self, project_id, name, task_type, duration, work,
                    priority, status, is_critical, parent_id=None) -> TaskDto:
        with self._uow_factory() as uow:
            cls = {"TASK": Task, "MILESTONE": Milestone, "SUMMARY_TASK": SummaryTask}.get(task_type, Task)
            # Milestones always have duration 0
            if task_type == "MILESTONE":
                duration = 0
            t = cls(
                name=name, duration=duration, work=work,
                priority=priority, status=status, is_critical=is_critical,
                project_id=project_id, parent_id=parent_id,
            )
            uow.tasks.add(t)
            uow.commit()
            return _to_task_dto(t)

    def update_task(self, task_id, name, duration, work, priority, status,
                    is_critical, percent_complete) -> Optional[TaskDto]:
        with self._uow_factory() as uow:
            t = uow.tasks.get(task_id)
            if t is None:
                return None
            t.name = name
            if t.task_type != "MILESTONE":
                t.duration = duration
            t.work = work
            t.priority = priority
            t.status = status
            t.is_critical = is_critical
            t.percent_complete = max(0.0, min(1.0, percent_complete))
            uow.commit()
            return _to_task_dto(t)

    def delete_task(self, task_id) -> bool:
        with self._uow_factory() as uow:
            t = uow.tasks.get(task_id)
            if t is None:
                return False
            uow.tasks.delete(task_id)
            uow.commit()
            return True


# --------------------------------------------------------------------------- #
# ResourceService — full CRUD                                                 #
# --------------------------------------------------------------------------- #
class ResourceService(IResourceService):
    """
    CRUD over Resources. The polymorphic shape (Human / Material / Cost)
    is preserved on create — once a resource exists its inheritance type
    is fixed, because changing it after creation would leave subtype-only
    columns inconsistent. Update therefore touches only the editable
    fields of the existing subtype.
    """

    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def list_resources(self) -> List[ResourceDto]:
        with self._uow_factory() as uow:
            items = uow.resources.list_all()
            return [_to_resource_dto(r) for r in sorted(items, key=lambda x: x.name.lower())]

    def get_resource(self, resource_id) -> Optional[ResourceDto]:
        with self._uow_factory() as uow:
            r = uow.resources.get(resource_id)
            return _to_resource_dto(r) if r else None

    def create_resource(self, name, code, resource_type,
                        cost_per_hour, max_units,
                        email=None, role=None, skills=None,
                        unit=None, consumption_rate=None,
                        fixed_cost=None) -> ResourceDto:
        with self._uow_factory() as uow:
            common = dict(
                name=name, code=code,
                cost_per_hour=cost_per_hour, max_units=max_units,
            )
            if resource_type == "HUMAN_RESOURCE":
                obj = HumanResource(**common, email=email, role=role, skills=skills)
            elif resource_type == "MATERIAL_RESOURCE":
                obj = MaterialResource(**common, unit=unit,
                                       consumption_rate=consumption_rate)
            elif resource_type == "COST_RESOURCE":
                obj = CostResource(**common, fixed_cost=fixed_cost)
            else:
                raise ValueError(f"Unknown resource type: {resource_type!r}")

            uow.resources.add(obj)
            uow.commit()
            return _to_resource_dto(obj)

    def update_resource(self, resource_id, name, code, cost_per_hour, max_units,
                        email=None, role=None, skills=None,
                        unit=None, consumption_rate=None,
                        fixed_cost=None) -> Optional[ResourceDto]:
        with self._uow_factory() as uow:
            r = uow.resources.get(resource_id)
            if r is None:
                return None
            r.name = name
            r.code = code
            r.cost_per_hour = cost_per_hour
            r.max_units = max_units

            # Only touch the subtype-specific fields that belong to this resource.
            if r.resource_type == "HUMAN_RESOURCE":
                r.email = email
                r.role = role
                r.skills = skills
            elif r.resource_type == "MATERIAL_RESOURCE":
                r.unit = unit
                r.consumption_rate = consumption_rate
            elif r.resource_type == "COST_RESOURCE":
                r.fixed_cost = fixed_cost

            uow.commit()
            return _to_resource_dto(r)

    def delete_resource(self, resource_id) -> bool:
        with self._uow_factory() as uow:
            r = uow.resources.get(resource_id)
            if r is None:
                return False
            uow.resources.delete(resource_id)
            uow.commit()
            return True


# --------------------------------------------------------------------------- #
# StatsService — dashboard aggregates                                         #
# --------------------------------------------------------------------------- #
class StatsService(IStatsService):
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def get_dashboard_stats(self) -> DashboardStats:
        with self._uow_factory() as uow:
            projects = uow.projects.list_all()
            tasks = uow.tasks.list_all()
            resources = uow.resources.list_all()
            assignments = uow.assignments.list_all()

            projects_by_status: Dict[str, int] = defaultdict(int)
            for p in projects:
                projects_by_status[p.status] += 1

            tasks_by_type: Dict[str, int] = defaultdict(int)
            for t in tasks:
                tasks_by_type[t.task_type] += 1

            resources_by_type: Dict[str, int] = defaultdict(int)
            for r in resources:
                resources_by_type[r.resource_type] += 1

            return DashboardStats(
                total_projects=len(projects),
                total_tasks=len(tasks),
                total_resources=len(resources),
                total_assignments=len(assignments),
                projects_by_status=dict(projects_by_status),
                tasks_by_type=dict(tasks_by_type),
                resources_by_type=dict(resources_by_type),
            )
