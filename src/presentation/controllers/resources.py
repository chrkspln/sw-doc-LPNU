"""
Resources controller — full CRUD on the organisation-wide resource pool.

Action methods:
    GET  /resources/                    list_resources
    GET  /resources/<id>                show_resource
    GET  /resources/new                 new_resource_form
    POST /resources/                    create_resource
    GET  /resources/<id>/edit           edit_resource_form
    POST /resources/<id>/edit           update_resource
    POST /resources/<id>/delete         delete_resource

The resource hierarchy is single-table polymorphic: a Resource is one of
Human, Material, or Cost. Type is chosen at creation time and locked
afterwards (changing inheritance type post-creation would orphan
subtype-specific columns). The form template hides irrelevant fields
based on the chosen type.
"""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ...bll.interfaces import IEventPublisher, IResourceService

RESOURCE_TYPES = ["HUMAN_RESOURCE", "MATERIAL_RESOURCE", "COST_RESOURCE"]


def _parse_float_field(value, default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_optional_float(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def create_resources_blueprint(
    resource_service: IResourceService,
    event_publisher: IEventPublisher,
) -> Blueprint:
    bp = Blueprint("resources", __name__, url_prefix="/resources")

    # ------------------------------------------------------------------ list
    @bp.route("/")
    def list_resources():
        items = resource_service.list_resources()
        return render_template("resources/list.html", resources=items)

    # ---------------------------------------------------------------- detail
    @bp.route("/<int:resource_id>")
    def show_resource(resource_id: int):
        r = resource_service.get_resource(resource_id)
        if r is None:
            abort(404)
        return render_template("resources/detail.html", resource=r)

    # --------------------------------------------------------------- create
    @bp.route("/new", methods=["GET"])
    def new_resource_form():
        return render_template(
            "resources/form.html",
            resource=None,
            resource_types=RESOURCE_TYPES,
            form_action=url_for("resources.create_resource"),
            heading="Create new resource",
        )

    @bp.route("/", methods=["POST"])
    def create_resource():
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip()
        if not name or not code:
            flash("Name and code are required.", "error")
            return redirect(url_for("resources.new_resource_form"))

        resource_type = request.form.get("resource_type", "HUMAN_RESOURCE")
        if resource_type not in RESOURCE_TYPES:
            flash(f"Unknown resource type: {resource_type}.", "error")
            return redirect(url_for("resources.new_resource_form"))

        r = resource_service.create_resource(
            name=name,
            code=code,
            resource_type=resource_type,
            cost_per_hour=_parse_float_field(request.form.get("cost_per_hour"), 0.0),
            max_units=_parse_float_field(request.form.get("max_units"), 1.0),
            email=request.form.get("email", "").strip() or None,
            role=request.form.get("role", "").strip() or None,
            skills=request.form.get("skills", "").strip() or None,
            unit=request.form.get("unit", "").strip() or None,
            consumption_rate=_parse_optional_float(request.form.get("consumption_rate")),
            fixed_cost=_parse_optional_float(request.form.get("fixed_cost")),
        )
        event_publisher.publish(
            action="resource.create",
            entity_type="resource",
            entity_id=r.id,
            details={"name": r.name, "resource_type": r.resource_type},
        )
        flash(f"Resource '{r.name}' created.", "success")
        return redirect(url_for("resources.show_resource", resource_id=r.id))

    # ----------------------------------------------------------------- edit
    @bp.route("/<int:resource_id>/edit", methods=["GET"])
    def edit_resource_form(resource_id: int):
        r = resource_service.get_resource(resource_id)
        if r is None:
            abort(404)
        return render_template(
            "resources/form.html",
            resource=r,
            resource_types=RESOURCE_TYPES,
            form_action=url_for("resources.update_resource", resource_id=resource_id),
            heading=f"Edit '{r.name}'",
        )

    @bp.route("/<int:resource_id>/edit", methods=["POST"])
    def update_resource(resource_id: int):
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip()
        if not name or not code:
            flash("Name and code are required.", "error")
            return redirect(url_for("resources.edit_resource_form", resource_id=resource_id))

        updated = resource_service.update_resource(
            resource_id=resource_id,
            name=name,
            code=code,
            cost_per_hour=_parse_float_field(request.form.get("cost_per_hour"), 0.0),
            max_units=_parse_float_field(request.form.get("max_units"), 1.0),
            email=request.form.get("email", "").strip() or None,
            role=request.form.get("role", "").strip() or None,
            skills=request.form.get("skills", "").strip() or None,
            unit=request.form.get("unit", "").strip() or None,
            consumption_rate=_parse_optional_float(request.form.get("consumption_rate")),
            fixed_cost=_parse_optional_float(request.form.get("fixed_cost")),
        )
        if updated is None:
            abort(404)
        event_publisher.publish(
            action="resource.update",
            entity_type="resource",
            entity_id=updated.id,
            details={"name": updated.name, "resource_type": updated.resource_type},
        )
        flash(f"Resource '{updated.name}' updated.", "success")
        return redirect(url_for("resources.show_resource", resource_id=resource_id))

    # --------------------------------------------------------------- delete
    @bp.route("/<int:resource_id>/delete", methods=["POST"])
    def delete_resource(resource_id: int):
        ok = resource_service.delete_resource(resource_id)
        if not ok:
            abort(404)
        event_publisher.publish(
            action="resource.delete",
            entity_type="resource",
            entity_id=resource_id,
        )
        flash("Resource deleted.", "success")
        return redirect(url_for("resources.list_resources"))

    return bp
