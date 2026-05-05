"""
Home controller.

Renders the dashboard page with aggregate stats. Depends only on
`IStatsService` from the BLL.
"""
from __future__ import annotations

from flask import Blueprint, render_template

from ...bll.interfaces import IStatsService


def create_home_blueprint(stats_service: IStatsService) -> Blueprint:
    bp = Blueprint("home", __name__)

    @bp.route("/")
    def index():
        stats = stats_service.get_dashboard_stats()
        return render_template("home.html", stats=stats)

    return bp
