"""
Resources controller — read-only views.

Resources are organization-wide and aren't created through the web UI in
this iteration; this controller just exposes a catalog view so the
template can display them alongside the rest of the data.
"""
from __future__ import annotations

from flask import Blueprint, abort, render_template

from ...bll.interfaces import IResourceService


def create_resources_blueprint(resource_service: IResourceService) -> Blueprint:
    bp = Blueprint("resources", __name__, url_prefix="/resources")

    @bp.route("/")
    def list_resources():
        items = resource_service.list_resources()
        return render_template("resources/list.html", resources=items)

    @bp.route("/<int:resource_id>")
    def show_resource(resource_id: int):
        r = resource_service.get_resource(resource_id)
        if r is None:
            abort(404)
        return render_template("resources/detail.html", resource=r)

    return bp
