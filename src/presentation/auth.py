"""
Firebase Authentication integration.

The browser logs in via the Firebase JS SDK on the /login page. After a
successful sign-in, the browser sends the resulting ID token to
/auth/login on the Flask backend. This module:

    1. Verifies the ID token using firebase-admin.
    2. Stores the user's email + uid in the Flask session.
    3. Provides @login_required for routes that need protection.

The session cookie is the standard Flask one — signed by SECRET_KEY so
it can't be forged. The Firebase ID token is validated only at login
time; subsequent requests trust the cookie until session expiry.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Optional

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

logger = logging.getLogger(__name__)


def init_firebase_admin(credentials_path: str) -> None:
    """Initialise firebase-admin once per process (idempotent)."""
    import firebase_admin
    from firebase_admin import credentials

    if not firebase_admin._apps:
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialised for auth")


def current_user() -> Optional[dict]:
    """Return {'uid', 'email'} for the logged-in user, or None."""
    uid = session.get("uid")
    if not uid:
        return None
    return {"uid": uid, "email": session.get("email", "")}


def login_required(view):
    """Bounce unauthenticated requests to /login."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            # Remember where they wanted to go so we can return them after login.
            return redirect(url_for("auth.login_page", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def create_auth_blueprint() -> Blueprint:
    bp = Blueprint("auth", __name__)

    @bp.route("/login")
    def login_page():
        if current_user():
            return redirect(url_for("home.index"))
        return render_template("auth/login.html",
                               next_url=request.args.get("next", ""))

    @bp.route("/auth/login", methods=["POST"])
    def login_submit():
        """Browser-side JS posts {idToken: "..."} here after Firebase login."""
        from firebase_admin import auth as fb_auth

        payload = request.get_json(silent=True) or {}
        token = payload.get("idToken")
        if not token:
            return jsonify({"ok": False, "error": "Missing idToken"}), 400

        try:
            decoded = fb_auth.verify_id_token(token)
        except Exception as exc:
            logger.warning("ID token verification failed: %s", exc)
            return jsonify({"ok": False, "error": "Invalid token"}), 401

        session["uid"] = decoded["uid"]
        session["email"] = decoded.get("email", "")
        session.permanent = True
        logger.info("User logged in: %s (%s)", session["email"], session["uid"])
        return jsonify({"ok": True, "email": session["email"]})

    @bp.route("/logout", methods=["POST", "GET"])
    def logout():
        session.clear()
        return redirect(url_for("auth.login_page"))

    return bp
