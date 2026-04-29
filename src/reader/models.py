"""
Domain model: a single NCDC Storm Events record.

The NCDC Storm Events Database (https://www.ncdc.noaa.gov/stormevents/)
publishes CSV files with ~50 columns per event. This model captures the
fields most commonly used for analysis. Unused columns from the source
file are silently ignored by the reader.

The model is deliberately a plain dataclass (no SQLAlchemy, no business
logic) so the output strategies can serialize it freely — to JSON, CSV,
formatted text, or whatever wire format a sink requires.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class StormEvent:
    # Identity
    event_id: str
    episode_id: Optional[str] = None

    # Classification
    event_type: str = ""              # Tornado, Hail, Flash Flood, etc.
    state: str = ""
    state_fips: Optional[int] = None
    cz_name: Optional[str] = None     # county / zone name
    wfo: Optional[str] = None         # weather forecast office code

    # Time
    year: Optional[int] = None
    month_name: Optional[str] = None
    begin_date_time: Optional[datetime] = None
    end_date_time: Optional[datetime] = None

    # Severity
    magnitude: Optional[float] = None
    magnitude_type: Optional[str] = None      # EG (estimated gust), MG (measured), etc.
    tor_f_scale: Optional[str] = None         # tornado F/EF scale

    # Impact
    injuries_direct: int = 0
    injuries_indirect: int = 0
    deaths_direct: int = 0
    deaths_indirect: int = 0
    damage_property: Optional[str] = None     # NCDC formats e.g. "1.20M"
    damage_crops: Optional[str] = None

    # Geography
    begin_lat: Optional[float] = None
    begin_lon: Optional[float] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None

    # Provenance
    source: Optional[str] = None
    event_narrative: Optional[str] = None

    # ---------- Helpers used by output strategies --------------------------- #
    def to_dict(self) -> Dict[str, Any]:
        """Plain-dict representation (datetimes stringified for JSON-friendliness)."""
        d = asdict(self)
        for k, v in list(d.items()):
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    @property
    def total_casualties(self) -> int:
        return (
            self.injuries_direct + self.injuries_indirect
            + self.deaths_direct + self.deaths_indirect
        )

    @property
    def location_label(self) -> str:
        if self.cz_name and self.state:
            return f"{self.cz_name.title()}, {self.state.title()}"
        return self.state.title() or "—"
