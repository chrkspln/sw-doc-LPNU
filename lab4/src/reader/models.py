"""
Domain model: a single record from the NCDC Storm Events Database.

Mirrors the 51-column schema published by NCEI/NOAA in their bulk CSV
files (`StormEvents_details-ftp_v1.0_dYYYY_cYYYYMMDD.csv.gz`), documented at
https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/Storm-Data-Bulk-csv-Format.pdf.

Every column from the real bulk file is preserved here. The reader is a
straight one-to-one mapping — no fields are dropped during ingestion.

The columns appear in the same order as the real CSV header, which makes
diffs against `head -1 StormEvents_details-*.csv` easy to verify.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class StormEvent:
    # Split begin/end timestamps (NCDC keeps both forms)
    begin_yearmonth: Optional[int] = None
    begin_day: Optional[int] = None
    begin_time: Optional[int] = None
    end_yearmonth: Optional[int] = None
    end_day: Optional[int] = None
    end_time: Optional[int] = None

    # Identity
    episode_id: Optional[str] = None
    event_id: str = ""

    # Geography
    state: str = ""
    state_fips: Optional[int] = None

    # Calendar context
    year: Optional[int] = None
    month_name: Optional[str] = None

    # Classification
    event_type: str = ""
    cz_type: Optional[str] = None
    cz_fips: Optional[int] = None
    cz_name: Optional[str] = None
    wfo: Optional[str] = None

    # Combined timestamps
    begin_date_time: Optional[datetime] = None
    cz_timezone: Optional[str] = None
    end_date_time: Optional[datetime] = None

    # Impact
    injuries_direct: int = 0
    injuries_indirect: int = 0
    deaths_direct: int = 0
    deaths_indirect: int = 0
    damage_property: Optional[str] = None
    damage_crops: Optional[str] = None

    # Reporting
    source: Optional[str] = None

    # Severity
    magnitude: Optional[float] = None
    magnitude_type: Optional[str] = None
    flood_cause: Optional[str] = None
    category: Optional[str] = None

    # Tornado-specific
    tor_f_scale: Optional[str] = None
    tor_length: Optional[float] = None
    tor_width: Optional[int] = None
    tor_other_wfo: Optional[str] = None
    tor_other_cz_state: Optional[str] = None
    tor_other_cz_fips: Optional[int] = None
    tor_other_cz_name: Optional[str] = None

    # Begin/end point
    begin_range: Optional[float] = None
    begin_azimuth: Optional[str] = None
    begin_location: Optional[str] = None
    end_range: Optional[float] = None
    end_azimuth: Optional[str] = None
    end_location: Optional[str] = None

    # Lat/Lon
    begin_lat: Optional[float] = None
    begin_lon: Optional[float] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None

    # Free-text narratives
    episode_narrative: Optional[str] = None
    event_narrative: Optional[str] = None

    # Provenance
    data_source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Plain-dict representation; datetimes serialised as ISO strings."""
        d = asdict(self)
        for k, v in list(d.items()):
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d
