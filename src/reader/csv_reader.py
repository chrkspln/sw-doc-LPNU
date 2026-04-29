"""
CSV reader for NCDC Storm Events files.

The real NCDC files have 51 columns; this reader picks out the ones the
`StormEvent` model knows about and ignores the rest. Empty cells are
treated as missing values (None/0 depending on the type).

Date/time handling: NCDC stores datetimes as 'DD-MMM-YY HH:MM:SS' in the
BEGIN_DATE_TIME / END_DATE_TIME columns. The reader parses that format
and falls back to None on anything it can't decode.
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime
from typing import Iterator, Optional

from .interfaces import IStormEventReader
from .models import StormEvent

logger = logging.getLogger(__name__)


def _parse_datetime(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%d-%b-%y %H:%M:%S", "%d-%b-%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _to_int(raw: str, default: int = 0) -> int:
    if not raw:
        return default
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        return default


def _to_float(raw: str) -> Optional[float]:
    if not raw:
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


class CsvStormEventReader(IStormEventReader):
    def __init__(self, path: str, limit: Optional[int] = None) -> None:
        self._path = path
        self._limit = limit

    def read(self) -> Iterator[StormEvent]:
        logger.info("Reading storm events from %s (limit=%s)", self._path, self._limit)
        count = 0
        with open(self._path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._limit is not None and count >= self._limit:
                    break
                yield self._row_to_event(row)
                count += 1
        logger.info("Finished reading: %d events", count)

    def _row_to_event(self, r: dict) -> StormEvent:
        # NCDC column names are upper-case; tolerate either form.
        def col(*names):
            for n in names:
                if n in r:
                    return r[n]
                lower = n.lower()
                if lower in r:
                    return r[lower]
            return ""

        return StormEvent(
            event_id=col("EVENT_ID") or "",
            episode_id=_str_or_none(col("EPISODE_ID")),
            event_type=col("EVENT_TYPE") or "",
            state=col("STATE") or "",
            state_fips=_to_int(col("STATE_FIPS"), default=0) or None,
            cz_name=_str_or_none(col("CZ_NAME")),
            wfo=_str_or_none(col("WFO")),
            year=_to_int(col("YEAR"), default=0) or None,
            month_name=_str_or_none(col("MONTH_NAME")),
            begin_date_time=_parse_datetime(col("BEGIN_DATE_TIME")),
            end_date_time=_parse_datetime(col("END_DATE_TIME")),
            magnitude=_to_float(col("MAGNITUDE")),
            magnitude_type=_str_or_none(col("MAGNITUDE_TYPE")),
            tor_f_scale=_str_or_none(col("TOR_F_SCALE")),
            injuries_direct=_to_int(col("INJURIES_DIRECT")),
            injuries_indirect=_to_int(col("INJURIES_INDIRECT")),
            deaths_direct=_to_int(col("DEATHS_DIRECT")),
            deaths_indirect=_to_int(col("DEATHS_INDIRECT")),
            damage_property=_str_or_none(col("DAMAGE_PROPERTY")),
            damage_crops=_str_or_none(col("DAMAGE_CROPS")),
            begin_lat=_to_float(col("BEGIN_LAT")),
            begin_lon=_to_float(col("BEGIN_LON")),
            end_lat=_to_float(col("END_LAT")),
            end_lon=_to_float(col("END_LON")),
            source=_str_or_none(col("SOURCE")),
            event_narrative=_str_or_none(col("EVENT_NARRATIVE")),
        )
