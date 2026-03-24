"""
BLL — DataImportService.
    1. Asks the DAL (via interface) to read CSV rows.
    2. Groups rows by record_type and inserts them in an order that
       respects foreign-key dependencies:
           Project -> Calendar / Baseline / Resource ->
           SummaryTask -> Task -> Milestone -> Dependency -> Assignment
    3. Maintains in-memory ext_id -> primary_key maps so that later
       rows can resolve their parent IDs without re-querying the DB.
    4. Wraps the whole thing in a single Unit of Work transaction —
       a failure mid-import rolls back cleanly.

The service depends on `ICsvDataReader` and `IUnitOfWork` only.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

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
    SummaryTask,
    Task,
)
from .interfaces import IDataImportService, ImportReport

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Small parsing helpers (private to the module)                               #
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
    return int(float(value))  # tolerate "8.0" in addition to "8"


def _parse_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _parse_bool(value) -> bool:
    if value is None or value == "":
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def _attr(record: CsvRecord, name: str):
    """Safe attribute access that always returns None if missing."""
    return getattr(record, name, None)


# --------------------------------------------------------------------------- #
# DataImportService                                                           #
# --------------------------------------------------------------------------- #
class DataImportService(IDataImportService):
    def __init__(self, csv_reader: ICsvDataReader, uow: IUnitOfWork) -> None:
        self._csv_reader = csv_reader
        self._uow = uow

    def import_from_csv(self, path: str) -> ImportReport:
        report = ImportReport()
        records: List[CsvRecord] = list(self._csv_reader.read(path))
        logger.info("Read %d records from %s", len(records), path)

        grouped: Dict[str, List[CsvRecord]] = defaultdict(list)
        for r in records:
            rt = _attr(r, "record_type")
            if rt:
                grouped[rt].append(r)

        # ext_id -> primary key tables for FK resolution
        project_ids: Dict[str, int] = {}
        task_ids: Dict[str, int] = {}
        resource_ids: Dict[str, int] = {}

        with self._uow as uow:
            try:
                self._import_projects(grouped["PROJECT"], uow, project_ids, report)
                self._import_calendars(grouped["CALENDAR"], uow, project_ids, report)
                self._import_baselines(grouped["BASELINE"], uow, project_ids, report)
                self._import_resources(
                    grouped["HUMAN_RESOURCE"]
                    + grouped["MATERIAL_RESOURCE"]
                    + grouped["COST_RESOURCE"],
                    uow,
                    resource_ids,
                    report,
                )
                # Summary tasks first so regular tasks can reference them as parents.
                self._import_tasks(grouped["SUMMARY_TASK"], uow, project_ids, task_ids, report)
                self._import_tasks(grouped["TASK"], uow, project_ids, task_ids, report)
                self._import_tasks(grouped["MILESTONE"], uow, project_ids, task_ids, report)
                self._import_dependencies(grouped["DEPENDENCY"], uow, task_ids, report)
                self._import_assignments(grouped["ASSIGNMENT"], uow, task_ids, resource_ids, report)

                uow.commit()
                logger.info("Import committed: %s", report)
            except Exception as exc:  # rollback is handled by the UoW itself
                logger.exception("Import failed; rolling back")
                report.errors.append(str(exc))
                raise

        return report

    # ---- per-type importers ------------------------------------------------ #
    def _import_projects(
        self,
        rows: Iterable[CsvRecord],
        uow: IUnitOfWork,
        project_ids: Dict[str, int],
        report: ImportReport,
    ) -> None:
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
            cal = Calendar(
                project_id=proj_id,
                working_days=_attr(r, "working_days") or "MON;TUE;WED;THU;FRI",
                working_hours=_attr(r, "working_hours") or "09:00-18:00",
            )
            uow.calendars.add(cal)
            report.calendars_created += 1

    def _import_baselines(self, rows, uow, project_ids, report):
        for r in rows:
            proj_id = project_ids.get(_attr(r, "project_ext_id"))
            if proj_id is None:
                report.skipped += 1
                continue
            b = Baseline(
                project_id=proj_id,
                saved_date=_parse_date(_attr(r, "saved_date")) or date.today(),
            )
            uow.baselines.add(b)
            report.baselines_created += 1

    def _import_resources(
        self,
        rows: Iterable[CsvRecord],
        uow: IUnitOfWork,
        resource_ids: Dict[str, int],
        report: ImportReport,
    ) -> None:
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
                obj = HumanResource(
                    **common,
                    email=_attr(r, "email"),
                    role=_attr(r, "role"),
                    skills=_attr(r, "skills"),
                )
            elif rt == "MATERIAL_RESOURCE":
                obj = MaterialResource(
                    **common,
                    unit=_attr(r, "unit"),
                    consumption_rate=_parse_float(_attr(r, "consumption_rate")),
                )
            elif rt == "COST_RESOURCE":
                obj = CostResource(
                    **common,
                    fixed_cost=_parse_float(_attr(r, "fixed_cost")),
                )
            else:
                report.skipped += 1
                continue

            uow.resources.add(obj)
            if r.ext_id:
                resource_ids[r.ext_id] = obj.id
            report.resources_created += 1

    def _import_tasks(
        self,
        rows: Iterable[CsvRecord],
        uow: IUnitOfWork,
        project_ids: Dict[str, int],
        task_ids: Dict[str, int],
        report: ImportReport,
    ) -> None:
        for r in rows:
            proj_id = project_ids.get(_attr(r, "project_ext_id"))
            if proj_id is None:
                report.skipped += 1
                continue

            parent_id: Optional[int] = None
            summary_ext = _attr(r, "summary_ext_id")
            if summary_ext:
                parent_id = task_ids.get(summary_ext)  # may be None — that's OK

            cls = {
                "TASK": Task,
                "MILESTONE": Milestone,
                "SUMMARY_TASK": SummaryTask,
            }.get(_attr(r, "record_type"), Task)

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

    def _import_dependencies(
        self,
        rows: Iterable[CsvRecord],
        uow: IUnitOfWork,
        task_ids: Dict[str, int],
        report: ImportReport,
    ) -> None:
        for r in rows:
            pred = task_ids.get(_attr(r, "predecessor_ext_id"))
            succ = task_ids.get(_attr(r, "successor_ext_id"))
            if pred is None or succ is None or pred == succ:
                report.skipped += 1
                continue
            d = Dependency(
                predecessor_id=pred,
                successor_id=succ,
                dep_type=_attr(r, "dep_type") or "FS",
                lag=_parse_int(_attr(r, "lag")),
            )
            uow.dependencies.add(d)
            report.dependencies_created += 1

    def _import_assignments(
        self,
        rows: Iterable[CsvRecord],
        uow: IUnitOfWork,
        task_ids: Dict[str, int],
        resource_ids: Dict[str, int],
        report: ImportReport,
    ) -> None:
        for r in rows:
            tid = task_ids.get(_attr(r, "task_ext_id"))
            rid = resource_ids.get(_attr(r, "resource_ext_id"))
            if tid is None or rid is None:
                report.skipped += 1
                continue
            a = Assignment(
                task_id=tid,
                resource_id=rid,
                units=_parse_float(_attr(r, "units"), default=1.0),
                work=_parse_int(_attr(r, "work")),
                actual_work=_parse_int(_attr(r, "actual_work")),
                cost=_parse_float(_attr(r, "cost")),
            )
            uow.assignments.add(a)
            report.assignments_created += 1
