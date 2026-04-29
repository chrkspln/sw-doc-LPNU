"""
Console output strategy.

Prints each event to standard output. Three formats are supported via
config (`output.console.format`):

    pretty   — human-readable card with ANSI color (default)
    json     — one compact JSON object per line
    csv      — comma-separated header + rows

Optional ANSI coloring is auto-disabled when stdout isn't a TTY (e.g.
piped to a file), so redirecting still produces clean output.
"""
from __future__ import annotations

import csv
import json
import sys
from io import StringIO
from typing import Optional

from ...reader.models import StormEvent
from ..interfaces import IOutputStrategy


# ANSI colour codes — minimal, no external dep.
class _Color:
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    ITALIC = "\033[3m"
    TERRA = "\033[38;5;167m"     # warm terracotta, matches Lab 3 vibe
    INK = "\033[38;5;235m"
    SOFT = "\033[38;5;245m"
    CRIT = "\033[38;5;160m"      # deep red for casualties


def _supports_color(stream) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


class ConsoleOutputStrategy(IOutputStrategy):
    name = "console"

    def __init__(self, fmt: str = "pretty", color: bool = True) -> None:
        self._format = fmt
        self._use_color = color and _supports_color(sys.stdout)
        self._csv_writer: Optional[csv.writer] = None  # type: ignore
        self._csv_header_written = False

    def open(self) -> None:
        if self._format == "pretty":
            self._print_banner()
        elif self._format == "csv":
            self._csv_writer = csv.writer(sys.stdout)
            self._csv_header_written = False

    def write(self, event: StormEvent) -> None:
        if self._format == "json":
            print(json.dumps(event.to_dict(), default=str, ensure_ascii=False))
        elif self._format == "csv":
            self._write_csv_row(event)
        else:
            self._write_pretty(event)

    def close(self) -> None:
        if self._format == "pretty":
            sys.stdout.write(self._c(_Color.SOFT, "─" * 70 + "\n\n"))
            sys.stdout.flush()

    # ----- internals ------------------------------------------------------ #
    def _c(self, color: str, text: str) -> str:
        return f"{color}{text}{_Color.RESET}" if self._use_color else text

    def _print_banner(self) -> None:
        sys.stdout.write("\n")
        sys.stdout.write(self._c(_Color.SOFT, "─" * 70 + "\n"))
        sys.stdout.write(self._c(_Color.BOLD, "  NCDC STORM EVENTS  ")
                         + self._c(_Color.SOFT + _Color.ITALIC,
                                   "· streaming to console\n"))
        sys.stdout.write(self._c(_Color.SOFT, "─" * 70 + "\n\n"))

    def _write_pretty(self, e: StormEvent) -> None:
        out = sys.stdout

        # Header line: event id + type + magnitude/scale (right-aligned tag)
        tag = e.tor_f_scale or (
            f"{e.magnitude:g} {e.magnitude_type}" if e.magnitude is not None
            and e.magnitude_type else None
        )
        title = self._c(_Color.BOLD, f"{e.event_type or '—'}")
        ev_id = self._c(_Color.SOFT, f"#{e.event_id}")
        head = f"  {title}  {ev_id}"
        if tag:
            head += "  " + self._c(_Color.TERRA, f"[{tag}]")
        out.write(head + "\n")

        # Sub-line: location + when
        when = e.begin_date_time.strftime("%Y-%m-%d %H:%M") if e.begin_date_time else "—"
        out.write("  " + self._c(_Color.SOFT,
                                 f"{e.location_label}  ·  {when}") + "\n")

        # Impact line
        cas = e.total_casualties
        cas_color = _Color.CRIT if cas > 0 else _Color.SOFT
        impact = (
            f"deaths {e.deaths_direct + e.deaths_indirect}  "
            f"injuries {e.injuries_direct + e.injuries_indirect}  "
            f"property {e.damage_property or '—'}  "
            f"crops {e.damage_crops or '—'}"
        )
        out.write("  " + self._c(cas_color, impact) + "\n")

        # Optional narrative — short excerpt only
        if e.event_narrative:
            snippet = e.event_narrative.strip().replace("\n", " ")
            if len(snippet) > 100:
                snippet = snippet[:97] + "…"
            out.write("  " + self._c(_Color.DIM + _Color.ITALIC, snippet) + "\n")

        out.write("\n")

    def _write_csv_row(self, e: StormEvent) -> None:
        d = e.to_dict()
        if not self._csv_header_written:
            self._csv_writer.writerow(d.keys())
            self._csv_header_written = True
        self._csv_writer.writerow(d.values())
