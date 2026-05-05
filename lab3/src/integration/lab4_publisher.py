"""
IEventPublisher implementation that ships events to Lab 4 by subprocess.

This is the integration seam between Lab 3 (Flask MVC web app) and Lab 4
(Strategy-pattern event pipeline). Lab 3's controllers call
`publish(...)` after every successful CRUD operation; this class spawns
a one-shot Lab 4 process, writes the event JSON to its stdin, and waits
briefly for it to finish.

Why subprocess and not in-process import?
    The lab assignment treats Lab 3 and Lab 4 as separate applications.
    A subprocess boundary makes that explicit at the OS level — Lab 4's
    config, dependencies, and Firebase credentials live in its own
    process. The cost is a fresh Python interpreter per click (~0.5–1 s);
    that's acceptable for the defence demo and is documented as the
    deliberate choice.

Failure mode:
    If the subprocess crashes (Lab 4 unreachable, Firestore down, JSON
    malformed), `publish` logs the failure and returns normally so the
    web request that triggered it still completes. The user sees a
    successful CRUD result; the missing audit log shows up in the Lab 3
    server log.

User attribution:
    The publisher takes a `user_provider` callable — a function that
    returns the email of the currently logged-in user, or "anonymous"
    if none. Wired in app.py to read from the Flask session.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from ..bll.interfaces import IEventPublisher

logger = logging.getLogger(__name__)


def _default_user_provider() -> str:
    return "anonymous"


class Lab4SubprocessPublisher(IEventPublisher):
    def __init__(
        self,
        lab4_dir: str,
        config_path: str = "config.yaml",
        timeout_seconds: float = 8.0,
        user_provider: Callable[[], str] = _default_user_provider,
    ) -> None:
        self._lab4_dir = Path(lab4_dir).resolve()
        self._config_path = config_path
        self._timeout = timeout_seconds
        self._user_provider = user_provider

        if not self._lab4_dir.exists():
            logger.warning("Lab 4 directory %s does not exist — events will fail silently",
                           self._lab4_dir)

    def publish(self, action: str, entity_type: str,
                entity_id: Optional[str] = None,
                details: Optional[dict] = None) -> None:
        try:
            user = self._user_provider()
        except Exception:
            user = "anonymous"

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "user": user,
            "details": details or {},
        }

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "src.main",
                 "--config", self._config_path],
                cwd=str(self._lab4_dir),
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
            if proc.returncode != 0:
                logger.warning(
                    "Lab 4 subprocess exited with %d for action=%s: stderr=%s",
                    proc.returncode, action, proc.stderr.strip()[:500],
                )
            else:
                logger.info("Published event %s for %s/%s via Lab 4 (user=%s)",
                            action, entity_type, entity_id, user)
        except subprocess.TimeoutExpired:
            logger.warning("Lab 4 subprocess timed out for action=%s", action)
        except Exception as exc:
            # Last-resort guard — audit logging must never break the request.
            logger.warning("Failed to publish event %s: %s", action, exc)
