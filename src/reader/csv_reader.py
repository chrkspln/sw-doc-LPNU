"""
CSV reader for real NCDC Storm Events bulk files.

Handles the production format published at
https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/, which differs
from naïve assumptions in three ways worth being aware of:

1. **Datetime format** is `MM/DD/YYYY hh:mm:ss` (24-hour, usually LST),
   e.g. `04/1/2012 20:48:00`. Note the lack of zero-padding on the day
   in some rows. The legacy export format uses `dd-MMM-yy HH:MM:SS`.
   Both are tolerated.
2. **Gzip transparency** — bulk files are distributed as `.csv.gz`. The
   reader auto-detects the suffix and opens with `gzip.open` so users
   never have to manually decompress.
3. **Header case** — modern bulk files use UPPERCASE column names
   (`EVENT_ID`, `BEGIN_DATE_TIME`); some older or third-party copies use
   lowercase. The reader normalises by checking both forms.

The reader yields `StormEvent` objects, never lists, so the program can
stream a 12 MB compressed file (≈ 60k events for a recent year) through
a Strategy without loading everything into RAM.
"""
from __future__ import annotations

import csv
import gzip
import logging
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from typing import Iterator, Optional

from .interfaces import IStormEventReader
from .models import StormEvent

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Field-level parsing helpers                                                 #
# --------------------------------------------------------------------------- #
_DATETIME_FORMATS = (
    "%m/%d/%Y %H:%M:%S",     # NCDC bulk format (most common)
    "%-m/%-d/%Y %H:%M:%S",   # not a real strptime token but kept for docs
    "%d-%b-%y %H:%M:%S",     # legacy export format (e.g. "15-MAY-24 14:30:00")
    "%d-%b-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",     # ISO-ish fallback
    "%Y-%m-%dT%H:%M:%S",
)


def _parse_datetime(raw: str) -> Optional[datetime]:
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    for fmt in _DATETIME_FORMATS:
        if "%-" in fmt:
            continue                       # documentation-only entry
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # Fallback: tolerate single-digit month/day in the NCDC format
    # (Python's strptime accepts these in %m/%d on most platforms,
    # but be belt-and-braces about it).
    try:
        date_part, time_part = s.split(" ", 1)
        m, d, y = (int(x) for x in date_part.split("/"))
        h, mn, sc = (int(x) for x in time_part.split(":"))
        return datetime(y, m, d, h, mn, sc)
    except (ValueError, IndexError):
        return None


def _to_int(raw: str) -> Optional[int]:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        return None


def _to_int_default(raw: str, default: int = 0) -> int:
    v = _to_int(raw)
    return default if v is None else v


def _to_float(raw: str) -> Optional[float]:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _str_or_none(raw: str) -> Optional[str]:
    if raw is None:
        return None
    s = raw.strip()
    return s if s else None


# --------------------------------------------------------------------------- #
# CsvStormEventReader                                                         #
# --------------------------------------------------------------------------- #
class CsvStormEventReader(IStormEventReader):
    """Reads a real NCDC Storm Events bulk CSV file (plain or gzipped)."""

    def __init__(self, path: str) -> None:
        self._path = path

    # ------------------------------------------------------------------ #
    def _open(self):
        """Open the file, transparently handling gzip."""
        p = Path(self._path)
        if p.suffix == ".gz":
            return TextIOWrapper(gzip.open(p, "rb"), encoding="utf-8",
                                 newline="")
        return open(p, "r", encoding="utf-8", newline="")

    # ------------------------------------------------------------------ #
    def read(self) -> Iterator[StormEvent]:
        logger.info("Reading storm events from %s", self._path)
        count = 0
        with self._open() as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                logger.warning("Empty CSV file at %s", self._path)
                return

            for row in reader:
                yield self._row_to_event(row)
                count += 1
        logger.info("Finished reading: %d events", count)

    # ------------------------------------------------------------------ #
    def _row_to_event(self, r: dict) -> StormEvent:
        """Map one raw CSV row → StormEvent.

        The mapping is one-to-one against the real 51-column NCDC schema.
        Column lookups tolerate either upper- or lower-case header names.
        """
        def col(name: str) -> str:
            # Try exact, then upper, then lower.
            if name in r:
                return r[name]
            up = name.upper()
            if up in r:
                return r[up]
            lo = name.lower()
            if lo in r:
                return r[lo]
            return ""

        return StormEvent(
            # split timestamps
            begin_yearmonth=_to_int(col("BEGIN_YEARMONTH")),
            begin_day=_to_int(col("BEGIN_DAY")),
            begin_time=_to_int(col("BEGIN_TIME")),
            end_yearmonth=_to_int(col("END_YEARMONTH")),
            end_day=_to_int(col("END_DAY")),
            end_time=_to_int(col("END_TIME")),

            # identity
            episode_id=_str_or_none(col("EPISODE_ID")),
            event_id=_str_or_none(col("EVENT_ID")) or "",

            # geography
            state=_str_or_none(col("STATE")) or "",
            state_fips=_to_int(col("STATE_FIPS")),

            # calendar
            year=_to_int(col("YEAR")),
            month_name=_str_or_none(col("MONTH_NAME")),

            # classification
            event_type=_str_or_none(col("EVENT_TYPE")) or "",
            cz_type=_str_or_none(col("CZ_TYPE")),
            cz_fips=_to_int(col("CZ_FIPS")),
            cz_name=_str_or_none(col("CZ_NAME")),
            wfo=_str_or_none(col("WFO")),

            # combined timestamps
            begin_date_time=_parse_datetime(col("BEGIN_DATE_TIME")),
            cz_timezone=_str_or_none(col("CZ_TIMEZONE")),
            end_date_time=_parse_datetime(col("END_DATE_TIME")),

            # impact
            injuries_direct=_to_int_default(col("INJURIES_DIRECT")),
            injuries_indirect=_to_int_default(col("INJURIES_INDIRECT")),
            deaths_direct=_to_int_default(col("DEATHS_DIRECT")),
            deaths_indirect=_to_int_default(col("DEATHS_INDIRECT")),
            damage_property=_str_or_none(col("DAMAGE_PROPERTY")),
            damage_crops=_str_or_none(col("DAMAGE_CROPS")),

            # reporting
            source=_str_or_none(col("SOURCE")),

            # severity
            magnitude=_to_float(col("MAGNITUDE")),
            magnitude_type=_str_or_none(col("MAGNITUDE_TYPE")),
            flood_cause=_str_or_none(col("FLOOD_CAUSE")),
            category=_str_or_none(col("CATEGORY")),

            # tornado-specific
            tor_f_scale=_str_or_none(col("TOR_F_SCALE")),
            tor_length=_to_float(col("TOR_LENGTH")),
            tor_width=_to_int(col("TOR_WIDTH")),
            tor_other_wfo=_str_or_none(col("TOR_OTHER_WFO")),
            tor_other_cz_state=_str_or_none(col("TOR_OTHER_CZ_STATE")),
            tor_other_cz_fips=_to_int(col("TOR_OTHER_CZ_FIPS")),
            tor_other_cz_name=_str_or_none(col("TOR_OTHER_CZ_NAME")),

            # begin point
            begin_range=_to_float(col("BEGIN_RANGE")),
            begin_azimuth=_str_or_none(col("BEGIN_AZIMUTH")),
            begin_location=_str_or_none(col("BEGIN_LOCATION")),
            # end point
            end_range=_to_float(col("END_RANGE")),
            end_azimuth=_str_or_none(col("END_AZIMUTH")),
            end_location=_str_or_none(col("END_LOCATION")),

            # lat/lon
            begin_lat=_to_float(col("BEGIN_LAT")),
            begin_lon=_to_float(col("BEGIN_LON")),
            end_lat=_to_float(col("END_LAT")),
            end_lon=_to_float(col("END_LON")),

            # narratives
            episode_narrative=_str_or_none(col("EPISODE_NARRATIVE")),
            event_narrative=_str_or_none(col("EVENT_NARRATIVE")),

            # provenance
            data_source=_str_or_none(col("DATA_SOURCE")),
        )
