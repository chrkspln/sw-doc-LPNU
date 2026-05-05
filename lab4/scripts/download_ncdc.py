"""
Download a real NCDC Storm Events bulk CSV file.

The NCDC publishes one ``StormEvents_details-ftp_v1.0_dYYYY_cYYYYMMDD.csv.gz``
per data year at:

    https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/

The "creation date" suffix changes whenever NCEI re-issues a year, so
the URL isn't fully predictable from the year alone. This script parses
the directory listing, finds the latest file for the requested year,
and downloads it.

Usage:
    python -m scripts.download_ncdc --year 2024
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

NCDC_BASE = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
USER_AGENT = "lab4-ncdc-fetch/1.0"

_DETAILS_RE = re.compile(
    r'StormEvents_details-ftp_v1\.0_d(\d{4})_c(\d{8})\.csv\.gz'
)


def _http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def find_latest_filename(year: int) -> Optional[str]:
    listing = _http_get(NCDC_BASE).decode("utf-8", errors="replace")
    candidates = []
    for m in _DETAILS_RE.finditer(listing):
        if int(m.group(1)) == year:
            candidates.append((m.group(2), m.group(0)))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def download_year(year: int, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = find_latest_filename(year)
    if filename is None:
        raise SystemExit(f"No details file found for year {year}.")

    url = NCDC_BASE + filename
    target = output_dir / filename

    print(f"Downloading {filename}…", file=sys.stderr)
    target.write_bytes(_http_get(url, timeout=120))
    print(f"  → wrote {target}", file=sys.stderr)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download a real NCDC Storm Events bulk CSV file."
    )
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args(argv)

    try:
        path = download_year(args.year, args.output)
    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1

    print(f"\nDone. Set input.file in config.yaml to:\n  {path}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
