"""
Projects controller — the main entity per Lab 3 spec.

Action methods:
    GET  /projects/                 list_projects     (with optional filters)
    GET  /projects/<id>             show_project      (detail page)
    GET  /projects/new              new_project_form  (create form)
    POST /projects/                 create_project    (form submit handler)
    GET  /projects/<id>/edit        edit_project_form (edit form)
    POST /projects/<id>/edit        update_project    (form submit handler)
    POST /projects/<id>/delete      delete_project    (with confirmation)
"""
from __future__ import annotations

from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ...bll.interfaces import IProjectService, ITaskService

PROJECT_STATUSES = ["PLANNED", "IN_PROGRESS", "COMPLETED", "ON_HOLD"]


def _parse_date_field(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def create_projects_blueprint(
    project_service: IProjectService,
    task_service: ITaskService,
) -> Blueprint:
    bp = Blueprint("projects", __name__, url_prefix="/projects")

    # ------------------------------------------------------------------ list
    @bp.route("/")
    def list_projects():
        search = request.args.get("q", "").strip() or None
        status = request.args.get("status", "").strip() or None
        projects = project_service.list_projects(search=search, status=status)
        return render_template(
            "projects/list.html",
            projects=projects,
            search=search or "",
            current_status=status or "",
            statuses=PROJECT_STATUSES,
        )

    # ---------------------------------------------------------------- detail
    @bp.route("/<int:project_id>")
    def show_project(project_id: int):
        detail = project_service.get_project_detail(project_id)
        if detail is None:
            abort(404)
        tasks = task_service.list_tasks_for_project(project_id)
        return render_template(
            "projects/detail.html",
            detail=detail,
            tasks=tasks,
        )

    # --------------------------------------------------------------- create
    @bp.route("/new", methods=["GET"])
    def new_project_form():
        return render_template(
            "projects/form.html",
            project=None,
            statuses=PROJECT_STATUSES,
            form_action=url_for("projects.create_project"),
            heading="Create new project",
        )

    @bp.route("/", methods=["POST"])
    def create_project():
        name = request.form.get("name", "").strip()
        if not name:
            flash("Project name is required.", "error")
            return redirect(url_for("projects.new_project_form"))

        project = project_service.create_project(
            name=name,
            description=request.form.get("description", "").strip() or None,
            start_date=_parse_date_field(request.form.get("start_date")),
            end_date=_parse_date_field(request.form.get("end_date")),
            status=request.form.get("status", "PLANNED"),
        )
        flash(f"Project '{project.name}' created.", "success")
        return redirect(url_for("projects.show_project", project_id=project.id))

    # ----------------------------------------------------------------- edit
    @bp.route("/<int:project_id>/edit", methods=["GET"])
    def edit_project_form(project_id: int):
        detail = project_service.get_project_detail(project_id)
        if detail is None:
            abort(404)
        return render_template(
            "projects/form.html",
            project=detail.project,
            statuses=PROJECT_STATUSES,
            form_action=url_for("projects.update_project", project_id=project_id),
            heading=f"Edit '{detail.project.name}'",
        )

    @bp.route("/<int:project_id>/edit", methods=["POST"])
    def update_project(project_id: int):
        name = request.form.get("name", "").strip()
        if not name:
            flash("Project name is required.", "error")
            return redirect(url_for("projects.edit_project_form", project_id=project_id))

        updated = project_service.update_project(
            project_id=project_id,
            name=name,
            description=request.form.get("description", "").strip() or None,
            start_date=_parse_date_field(request.form.get("start_date")),
            end_date=_parse_date_field(request.form.get("end_date")),
            status=request.form.get("status", "PLANNED"),
        )
        if updated is None:
            abort(404)
        flash(f"Project '{updated.name}' updated.", "success")
        return redirect(url_for("projects.show_project", project_id=project_id))

    # ------------------------------------------------------------- delete
    @bp.route("/<int:project_id>/delete", methods=["POST"])
    def delete_project(project_id: int):
        ok = project_service.delete_project(project_id)
        if not ok:
            abort(404)
        flash("Project deleted.", "success")
        return redirect(url_for("projects.list_projects"))

    return bp
