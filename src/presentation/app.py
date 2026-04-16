"""
Presentation — Flask application factory.

The factory takes a `Container` (composition root from `di/`) and
constructs a Flask app whose blueprints (controllers) receive their
service dependencies through closures. Controllers depend only on the
BLL interfaces; the choice of concrete service is a Container decision.

Adds in this iteration:
    - Firebase Authentication (server-side ID token verification)
    - All routes except /login and /auth/* require an authenticated session
    - Firebase Analytics web SDK injection via context processor
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from flask import Flask, redirect, request, url_for

from ..di.container import Container
from .auth import create_auth_blueprint, current_user, init_firebase_admin
from .controllers.home import create_home_blueprint
from .controllers.projects import create_projects_blueprint
from .controllers.tasks import create_tasks_blueprint
from .controllers.resources import create_resources_blueprint


# Endpoints that don't require authentication.
_PUBLIC_ENDPOINTS = {"auth.login_page", "auth.login_submit", "auth.logout", "static"}


def create_app(container: Container) -> Flask:
    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "lab3-dev-secret-change-me")
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

    # Initialise firebase-admin once for ID token verification.
    creds_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if creds_path:
        init_firebase_admin(creds_path)
    else:
        app.logger.warning(
            "FIREBASE_SERVICE_ACCOUNT not set — login will fail. "
            "Point it at your Firebase service-account JSON."
        )

    # Register blueprints
    app.register_blueprint(create_auth_blueprint())
    app.register_blueprint(create_home_blueprint(
        stats_service=container.stats_service(),
    ))
    app.register_blueprint(create_projects_blueprint(
        project_service=container.project_service(),
        task_service=container.task_service(),
        event_publisher=container.event_publisher(),
    ))
    app.register_blueprint(create_tasks_blueprint(
        task_service=container.task_service(),
        project_service=container.project_service(),
        event_publisher=container.event_publisher(),
    ))
    app.register_blueprint(create_resources_blueprint(
        resource_service=container.resource_service(),
        event_publisher=container.event_publisher(),
    ))

    # Global auth guard — bounce unauthenticated requests to /login.
    @app.before_request
    def require_login():
        if request.endpoint in _PUBLIC_ENDPOINTS:
            return None
        if request.endpoint is None:
            return None  # 404 handler will deal with it
        if current_user() is None:
            return redirect(url_for("auth.login_page", next=request.path))

    # Inject the public Firebase web config into every template so the
    # browser can initialize Firebase Analytics. Pulled from env vars so
    # the actual values stay out of the source tree.
    firebase_web_config = {
        "apiKey":            os.environ.get("FIREBASE_WEB_API_KEY", ""),
        "authDomain":        os.environ.get("FIREBASE_WEB_AUTH_DOMAIN", ""),
        "projectId":         os.environ.get("FIREBASE_WEB_PROJECT_ID", ""),
        "storageBucket":     os.environ.get("FIREBASE_WEB_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FIREBASE_WEB_MESSAGING_SENDER_ID", ""),
        "appId":             os.environ.get("FIREBASE_WEB_APP_ID", ""),
        "measurementId":     os.environ.get("FIREBASE_WEB_MEASUREMENT_ID", ""),
    }
    firebase_enabled = bool(firebase_web_config["apiKey"])

    @app.context_processor
    def inject_globals():
        return {
            "firebase_web_config": firebase_web_config,
            "firebase_enabled": firebase_enabled,
            "current_user": current_user(),
        }

    # ---- Jinja filters --------------------------------------------------- #
    @app.template_filter("status_class")
    def status_class(value: str) -> str:
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
