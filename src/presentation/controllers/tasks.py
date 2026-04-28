"""
Tasks controller — Task CRUD within a parent Project.

Action methods:
    GET  /projects/<pid>/tasks/new       new_task_form
    POST /projects/<pid>/tasks           create_task
    GET  /tasks/<tid>/edit               edit_task_form
    POST /tasks/<tid>/edit               update_task
    POST /tasks/<tid>/delete             delete_task
"""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ...bll.interfaces import IProjectService, ITaskService

TASK_TYPES = ["TASK", "MILESTONE", "SUMMARY_TASK"]
TASK_STATUSES = ["NOT_STARTED", "IN_PROGRESS", "COMPLETED", "ON_HOLD"]


def create_tasks_blueprint(
    task_service: ITaskService,
    project_service: IProjectService,
) -> Blueprint:
    bp = Blueprint("tasks", __name__)

    @bp.route("/projects/<int:project_id>/tasks/new", methods=["GET"])
    def new_task_form(project_id: int):
        detail = project_service.get_project_detail(project_id)
        if detail is None:
            abort(404)
        # Only summary tasks of this project can be selected as parents.
        possible_parents = [t for t in detail.tasks if t.task_type == "SUMMARY_TASK"]
        return render_template(
            "tasks/form.html",
            task=None,
            project=detail.project,
            task_types=TASK_TYPES,
            statuses=TASK_STATUSES,
            possible_parents=possible_parents,
            form_action=url_for("tasks.create_task", project_id=project_id),
            heading="Add task",
        )

    @bp.route("/projects/<int:project_id>/tasks", methods=["POST"])
    def create_task(project_id: int):
        name = request.form.get("name", "").strip()
        if not name:
            flash("Task name is required.", "error")
            return redirect(url_for("tasks.new_task_form", project_id=project_id))

        parent_raw = request.form.get("parent_id", "").strip()
        parent_id = int(parent_raw) if parent_raw else None

        try:
            duration = int(request.form.get("duration", "0"))
            work = int(request.form.get("work", "0"))
            priority = int(request.form.get("priority", "500"))
        except ValueError:
            flash("Numeric fields must be valid integers.", "error")
            return redirect(url_for("tasks.new_task_form", project_id=project_id))

        task = task_service.create_task(
            project_id=project_id,
            name=name,
            task_type=request.form.get("task_type", "TASK"),
            duration=duration,
            work=work,
            priority=priority,
            status=request.form.get("status", "NOT_STARTED"),
            is_critical=bool(request.form.get("is_critical")),
            parent_id=parent_id,
        )
        flash(f"Task '{task.name}' added.", "success")
        return redirect(url_for("projects.show_project", project_id=project_id))

    @bp.route("/tasks/<int:task_id>/edit", methods=["GET"])
    def edit_task_form(task_id: int):
        task = task_service.get_task(task_id)
        if task is None:
            abort(404)
        detail = project_service.get_project_detail(task.project_id)
        possible_parents = [t for t in detail.tasks if t.task_type == "SUMMARY_TASK" and t.id != task.id]
        return render_template(
            "tasks/form.html",
            task=task,
            project=detail.project,
            task_types=TASK_TYPES,
            statuses=TASK_STATUSES,
            possible_parents=possible_parents,
            form_action=url_for("tasks.update_task", task_id=task_id),
            heading=f"Edit task '{task.name}'",
        )

    @bp.route("/tasks/<int:task_id>/edit", methods=["POST"])
    def update_task(task_id: int):
        name = request.form.get("name", "").strip()
        if not name:
            flash("Task name is required.", "error")
            return redirect(url_for("tasks.edit_task_form", task_id=task_id))

        try:
            duration = int(request.form.get("duration", "0"))
            work = int(request.form.get("work", "0"))
            priority = int(request.form.get("priority", "500"))
            percent = float(request.form.get("percent_complete", "0"))
        except ValueError:
            flash("Numeric fields must be valid.", "error")
            return redirect(url_for("tasks.edit_task_form", task_id=task_id))

        updated = task_service.update_task(
            task_id=task_id,
            name=name,
            duration=duration,
            work=work,
            priority=priority,
            status=request.form.get("status", "NOT_STARTED"),
            is_critical=bool(request.form.get("is_critical")),
            percent_complete=percent,
        )
        if updated is None:
            abort(404)
        flash(f"Task '{updated.name}' updated.", "success")
        return redirect(url_for("projects.show_project", project_id=updated.project_id))

    @bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
    def delete_task(task_id: int):
        task = task_service.get_task(task_id)
        if task is None:
            abort(404)
        project_id = task.project_id
        task_service.delete_task(task_id)
        flash("Task deleted.", "success")
        return redirect(url_for("projects.show_project", project_id=project_id))

    return bp
