"""
DAL — ORM models.

These classes are the SQLAlchemy mapping of the entities from the class
diagram produced in Lab 1.b (Microsoft Project plan creation):

    Project, Task, Milestone, SummaryTask, Resource, HumanResource,
    MaterialResource, CostResource, Assignment, Dependency, Calendar, Baseline.

Inheritance is implemented via SQLAlchemy *single-table inheritance*:
- Task ─┬─ Milestone
       └─ SummaryTask        (one `tasks` table, discriminator column `task_type`)

- Resource ─┬─ HumanResource
            ├─ MaterialResource
            └─ CostResource    (one `resources` table, discriminator `resource_type`)

`ext_id` is an external identifier carried in from the CSV file. It is the
key that lets the BLL resolve cross-references (a Task to its Project, an
Assignment to its Task, etc.) without hard-coding numeric IDs in the file.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Single declarative base for the whole DAL."""


# --------------------------------------------------------------------------- #
# Project, Calendar, Baseline                                                 #
# --------------------------------------------------------------------------- #
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    ext_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="PLANNED")

    tasks: Mapped[List["Task"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    calendars: Mapped[List["Calendar"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    baselines: Mapped[List["Baseline"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} ext_id={self.ext_id} name={self.name!r}>"


class Calendar(Base):
    __tablename__ = "calendars"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    working_days: Mapped[str] = mapped_column(String(100), default="MON;TUE;WED;THU;FRI")
    working_hours: Mapped[str] = mapped_column(String(50), default="09:00-18:00")

    project: Mapped["Project"] = relationship(back_populates="calendars")


class Baseline(Base):
    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    saved_date: Mapped[date] = mapped_column(Date, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="baselines")


# --------------------------------------------------------------------------- #
# Task hierarchy (single-table inheritance)                                   #
# --------------------------------------------------------------------------- #
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    ext_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    duration: Mapped[int] = mapped_column(Integer, default=0)
    work: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    percent_complete: Mapped[float] = mapped_column(Float, default=0.0)
    priority: Mapped[int] = mapped_column(Integer, default=500)
    status: Mapped[str] = mapped_column(String(50), default="NOT_STARTED")
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)

    # Discriminator column — populated automatically by SQLAlchemy
    task_type: Mapped[str] = mapped_column(String(20), default="TASK")

    # FK: Task always belongs to a Project
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    # FK: Task may have a SummaryTask as its parent (self-referential)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"))

    project: Mapped["Project"] = relationship(back_populates="tasks")
    parent: Mapped[Optional["Task"]] = relationship(
        "Task", remote_side="Task.id", back_populates="subtasks"
    )
    subtasks: Mapped[List["Task"]] = relationship("Task", back_populates="parent")

    assignments: Mapped[List["Assignment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    incoming_dependencies: Mapped[List["Dependency"]] = relationship(
        "Dependency",
        foreign_keys="Dependency.successor_id",
        back_populates="successor",
        cascade="all, delete-orphan",
    )
    outgoing_dependencies: Mapped[List["Dependency"]] = relationship(
        "Dependency",
        foreign_keys="Dependency.predecessor_id",
        back_populates="predecessor",
        cascade="all, delete-orphan",
    )

    __mapper_args__ = {
        "polymorphic_on": "task_type",
        "polymorphic_identity": "TASK",
    }

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id} ext_id={self.ext_id} name={self.name!r}>"


class Milestone(Task):
    """A Task whose duration is always zero — represents a key checkpoint."""

    __mapper_args__ = {"polymorphic_identity": "MILESTONE"}


class SummaryTask(Task):
    """A Task that aggregates a set of child tasks (its subtasks)."""

    __mapper_args__ = {"polymorphic_identity": "SUMMARY_TASK"}


# --------------------------------------------------------------------------- #
# Resource hierarchy (single-table inheritance)                               #
# --------------------------------------------------------------------------- #
class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    ext_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    cost_per_hour: Mapped[float] = mapped_column(Float, default=0.0)
    max_units: Mapped[float] = mapped_column(Float, default=1.0)

    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Subclass-specific columns. With single-table inheritance these are
    # nullable on the table and only populated for the relevant subclass.
    email: Mapped[Optional[str]] = mapped_column(String(200))
    role: Mapped[Optional[str]] = mapped_column(String(100))
    skills: Mapped[Optional[str]] = mapped_column(Text)  # ';'-separated
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    consumption_rate: Mapped[Optional[float]] = mapped_column(Float)
    fixed_cost: Mapped[Optional[float]] = mapped_column(Float)

    assignments: Mapped[List["Assignment"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )

    __mapper_args__ = {
        "polymorphic_on": "resource_type",
        "polymorphic_identity": "RESOURCE",
    }

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id} ext_id={self.ext_id} name={self.name!r}>"


class HumanResource(Resource):
    __mapper_args__ = {"polymorphic_identity": "HUMAN_RESOURCE"}


class MaterialResource(Resource):
    __mapper_args__ = {"polymorphic_identity": "MATERIAL_RESOURCE"}


class CostResource(Resource):
    __mapper_args__ = {"polymorphic_identity": "COST_RESOURCE"}


# --------------------------------------------------------------------------- #
# Association class: Assignment (Task <-> Resource)                           #
# --------------------------------------------------------------------------- #
class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), nullable=False)

    units: Mapped[float] = mapped_column(Float, default=1.0)
    work: Mapped[int] = mapped_column(Integer, default=0)
    actual_work: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)

    task: Mapped["Task"] = relationship(back_populates="assignments")
    resource: Mapped["Resource"] = relationship(back_populates="assignments")


# --------------------------------------------------------------------------- #
# Dependency: Task -> Task                                                    #
# --------------------------------------------------------------------------- #
class Dependency(Base):
    __tablename__ = "dependencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    predecessor_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    successor_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    dep_type: Mapped[str] = mapped_column(String(2), default="FS")  # FS, SS, FF, SF
    lag: Mapped[int] = mapped_column(Integer, default=0)

    predecessor: Mapped["Task"] = relationship(
        foreign_keys=[predecessor_id], back_populates="outgoing_dependencies"
    )
    successor: Mapped["Task"] = relationship(
        foreign_keys=[successor_id], back_populates="incoming_dependencies"
    )
