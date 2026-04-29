"""
Generate a sample NCDC Storm Events CSV.

The real NCDC files are huge and gzipped. This script generates a
locally-runnable sample that uses the same column names and value
formats so the reader exercises the real parsing path.

    python -m scripts.generate_sample --output data/storm_events.csv --rows 200
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


# NCDC column order (subset — the real file has more, but real readers
# tolerate extra columns). These are the columns our reader looks at.
COLUMNS: List[str] = [
    "EVENT_ID", "EPISODE_ID", "EVENT_TYPE", "STATE", "STATE_FIPS",
    "YEAR", "MONTH_NAME", "BEGIN_DATE_TIME", "END_DATE_TIME",
    "CZ_NAME", "WFO",
    "INJURIES_DIRECT", "INJURIES_INDIRECT",
    "DEATHS_DIRECT", "DEATHS_INDIRECT",
    "DAMAGE_PROPERTY", "DAMAGE_CROPS",
    "MAGNITUDE", "MAGNITUDE_TYPE", "TOR_F_SCALE",
    "BEGIN_LAT", "BEGIN_LON", "END_LAT", "END_LON",
    "SOURCE", "EVENT_NARRATIVE",
]


# Real NCDC event-type vocabulary (a representative subset).
EVENT_TYPES = [
    "Tornado", "Hail", "Thunderstorm Wind", "Flash Flood", "Flood",
    "Winter Storm", "Heavy Snow", "Blizzard", "Ice Storm",
    "High Wind", "Strong Wind", "Heavy Rain", "Lightning",
    "Hurricane (Typhoon)", "Tropical Storm", "Wildfire",
    "Drought", "Excessive Heat", "Extreme Cold/Wind Chill",
    "Funnel Cloud", "Dust Devil", "Storm Surge/Tide",
    "Coastal Flood", "Rip Current", "Marine High Wind",
]

# US state names + their FIPS codes (a sample — enough for variety).
STATES_FIPS: Dict[str, int] = {
    "ALABAMA": 1, "ARKANSAS": 5, "CALIFORNIA": 6, "COLORADO": 8,
    "FLORIDA": 12, "GEORGIA": 13, "ILLINOIS": 17, "INDIANA": 18,
    "IOWA": 19, "KANSAS": 20, "KENTUCKY": 21, "LOUISIANA": 22,
    "MICHIGAN": 26, "MINNESOTA": 27, "MISSISSIPPI": 28, "MISSOURI": 29,
    "NEBRASKA": 31, "NEW MEXICO": 35, "NORTH CAROLINA": 37,
    "OHIO": 39, "OKLAHOMA": 40, "PENNSYLVANIA": 42, "TENNESSEE": 47,
    "TEXAS": 48, "VIRGINIA": 51, "WEST VIRGINIA": 54, "WISCONSIN": 55,
}

COUNTIES = [
    "JEFFERSON", "WASHINGTON", "FRANKLIN", "MADISON", "LINCOLN",
    "JACKSON", "MARION", "MONROE", "MONTGOMERY", "DALLAS",
    "HARRIS", "TRAVIS", "BEXAR", "TARRANT", "COLLIN",
    "ORANGE", "MIAMI-DADE", "BROWARD", "PALM BEACH", "HILLSBOROUGH",
    "COOK", "LAKE", "DUPAGE", "WILL", "KANE",
]

WFO_CODES = ["OUN", "BMX", "MEG", "TBW", "FFC", "JAN", "LZK", "EAX",
             "ICT", "DDC", "GLD", "GID", "OAX", "DMX", "ARX"]

MAGNITUDE_TYPES = ["EG", "MG", "MS", "ES"]
TOR_F_SCALES = ["EF0", "EF1", "EF2", "EF3", "EF4", "EF5"]
SOURCES = ["Trained Spotter", "Public", "Law Enforcement",
           "Emergency Manager", "Broadcast Media", "Newspaper",
           "NWS Storm Survey", "Department of Highways"]


def _rand_dt(year: int) -> datetime:
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31, 23, 59)
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def _format_dt(dt: datetime) -> str:
    """NCDC format: '15-MAY-24 14:30:00'."""
    return dt.strftime("%d-%b-%y %H:%M:%S").upper()


def _format_damage(amount_dollars: float) -> str:
    """NCDC format: '1.20M', '500.00K', '0.00K'."""
    if amount_dollars >= 1_000_000:
        return f"{amount_dollars / 1_000_000:.2f}M"
    return f"{amount_dollars / 1_000:.2f}K"


def _narrative(event_type: str, state: str) -> str:
    templates = [
        "A {et} was reported in {state}, causing damage to homes and infrastructure.",
        "Severe {et} affected the area; residents reported significant impacts.",
        "Trained spotters confirmed {et} in {state}; emergency services responded.",
        "Storm survey confirmed {et} with widespread effects across the county.",
        "{et} produced damaging conditions; multiple reports received.",
    ]
    return random.choice(templates).format(et=event_type.lower(), state=state.title())


def generate_rows(n: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    for i in range(n):
        event_type = random.choice(EVENT_TYPES)
        state, fips = random.choice(list(STATES_FIPS.items()))
        year = random.randint(2018, 2024)

        begin = _rand_dt(year)
        end = begin + timedelta(minutes=random.randint(5, 240))

        # Damage and casualties: long tail with most events small.
        if random.random() < 0.05:    # 5% major events
            prop_dmg = random.uniform(1_000_000, 50_000_000)
            crop_dmg = random.uniform(0, 5_000_000)
            inj_d = random.randint(0, 30)
            dth_d = random.randint(0, 5)
        elif random.random() < 0.25:  # 25% medium
            prop_dmg = random.uniform(50_000, 1_000_000)
            crop_dmg = random.uniform(0, 200_000)
            inj_d = random.randint(0, 5)
            dth_d = 0
        else:                          # rest minor
            prop_dmg = random.uniform(0, 50_000)
            crop_dmg = 0.0
            inj_d = 0
            dth_d = 0

        # Tornado-specific or magnitude-only fields.
        tor_scale = ""
        magnitude = ""
        magnitude_type = ""
        if event_type == "Tornado":
            tor_scale = random.choice(TOR_F_SCALES)
        elif event_type in ("Thunderstorm Wind", "High Wind", "Strong Wind",
                            "Marine High Wind", "Hurricane (Typhoon)"):
            magnitude = f"{random.randint(40, 130)}"
            magnitude_type = random.choice(MAGNITUDE_TYPES)
        elif event_type == "Hail":
            magnitude = f"{random.uniform(0.5, 4.0):.2f}"

        # Random latitude/longitude inside continental US.
        begin_lat = round(random.uniform(25.0, 49.0), 4)
        begin_lon = round(random.uniform(-124.0, -67.0), 4)
        end_lat = round(begin_lat + random.uniform(-0.2, 0.2), 4)
        end_lon = round(begin_lon + random.uniform(-0.2, 0.2), 4)

        rows.append({
            "EVENT_ID":         str(700000 + i),
            "EPISODE_ID":       str(150000 + i // 4),  # ~4 events per episode
            "EVENT_TYPE":       event_type,
            "STATE":            state,
            "STATE_FIPS":       str(fips),
            "YEAR":             str(year),
            "MONTH_NAME":       begin.strftime("%B"),
            "BEGIN_DATE_TIME":  _format_dt(begin),
            "END_DATE_TIME":    _format_dt(end),
            "CZ_NAME":          random.choice(COUNTIES),
            "WFO":              random.choice(WFO_CODES),
            "INJURIES_DIRECT":  str(inj_d),
            "INJURIES_INDIRECT": "0",
            "DEATHS_DIRECT":    str(dth_d),
            "DEATHS_INDIRECT":  "0",
            "DAMAGE_PROPERTY":  _format_damage(prop_dmg),
            "DAMAGE_CROPS":     _format_damage(crop_dmg),
            "MAGNITUDE":        magnitude,
            "MAGNITUDE_TYPE":   magnitude_type,
            "TOR_F_SCALE":      tor_scale,
            "BEGIN_LAT":        f"{begin_lat}",
            "BEGIN_LON":        f"{begin_lon}",
            "END_LAT":          f"{end_lat}",
            "END_LON":          f"{end_lon}",
            "SOURCE":           random.choice(SOURCES),
            "EVENT_NARRATIVE":  _narrative(event_type, state),
        })

    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a sample NCDC Storm Events CSV.")
    parser.add_argument("--output", type=Path, default=Path("data/storm_events.csv"))
    parser.add_argument("--rows", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    random.seed(args.seed)
    rows = generate_rows(args.rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    types_count: Dict[str, int] = {}
    for r in rows:
        types_count[r["EVENT_TYPE"]] = types_count.get(r["EVENT_TYPE"], 0) + 1

    print(f"Wrote {len(rows)} storm events to {args.output}")
    print("Top event types:")
    for t, n in sorted(types_count.items(), key=lambda kv: -kv[1])[:6]:
        print(f"  {t:30s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
