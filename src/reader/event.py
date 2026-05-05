"""
Domain model: a single application event.

Used for the Lab 3 → Lab 4 audit logging pipeline. Each click in the
Lab 3 web UI (project create / update / delete, task create / update /
delete, resource create / update / delete) produces one Event that
Lab 4 ships to whichever sink is configured.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class Event:
    """An action performed in the Lab 3 web UI."""

    timestamp: str                                   # ISO 8601 UTC
    action: str                                      # e.g. "project.create"
    entity_type: str                                 # "project" | "task" | "resource"
    entity_id: Optional[str] = None
    user: str = "anonymous"
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def now(cls, action: str, entity_type: str,
            entity_id: Optional[str] = None,
            user: str = "anonymous",
            details: Optional[Dict[str, Any]] = None) -> "Event":
        """Convenience: build an Event with `timestamp` set to UTC now."""
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            user=user,
            details=details or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
