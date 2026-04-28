"""
Presentation — Flask application factory.

The factory takes a `Container` (composition root from `di/`) and
constructs a Flask app whose blueprints (controllers) receive their
service dependencies through closures. Controllers depend only on the
BLL interfaces; the choice of concrete service is a Container decision.
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from ..di.container import Container
from .controllers.home import create_home_blueprint
from .controllers.projects import create_projects_blueprint
from .controllers.tasks import create_tasks_blueprint
from .controllers.resources import create_resources_blueprint


def create_app(container: Container) -> Flask:
    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = "lab3-dev-secret-change-me"

    app.register_blueprint(create_home_blueprint(
        stats_service=container.stats_service(),
    ))
    app.register_blueprint(create_projects_blueprint(
        project_service=container.project_service(),
        task_service=container.task_service(),
    ))
    app.register_blueprint(create_tasks_blueprint(
        task_service=container.task_service(),
        project_service=container.project_service(),
    ))
    app.register_blueprint(create_resources_blueprint(
        resource_service=container.resource_service(),
    ))

    @app.template_filter("status_class")
    def status_class(value: str) -> str:
        """CSS class for status pills."""
        return {
            "PLANNED": "pill-neutral",
            "IN_PROGRESS": "pill-active",
            "COMPLETED": "pill-success",
            "ON_HOLD": "pill-paused",
            "NOT_STARTED": "pill-neutral",
        }.get(value, "pill-neutral")

    @app.template_filter("task_type_label")
    def task_type_label(value: str) -> str:
        return {
            "TASK": "Task",
            "MILESTONE": "Milestone",
            "SUMMARY_TASK": "Summary",
        }.get(value, value)

    @app.template_filter("resource_type_label")
    def resource_type_label(value: str) -> str:
        return {
            "HUMAN_RESOURCE": "Human",
            "MATERIAL_RESOURCE": "Material",
            "COST_RESOURCE": "Cost",
        }.get(value, value)

    @app.template_filter("percent")
    def percent(value: float) -> str:
        if value is None:
            return "0%"
        return f"{int(round(value * 100))}%"

    @app.template_filter("money")
    def money(value: float) -> str:
        if value is None:
            return "—"
        return f"${value:,.2f}"

    return app
