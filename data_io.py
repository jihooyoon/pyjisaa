"""Data I/O — CSV reading and JSON serialization.

Ported from jisrot/src/data_io.rs.
Works directly with plain dicts — no data model classes.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from definitions import BILLING_ON_PATTERN, EVENT_TIME_PATTERN


def parse_time_str(time_string: str, pattern: str) -> datetime | None:
    """Parse a datetime string, with fallback from full datetime to date-only."""
    time_string = time_string.strip()
    if not time_string:
        return None

    # Try full datetime parse first
    try:
        return datetime.strptime(time_string, pattern)
    except ValueError:
        pass

    # Fallback: try date-only parse (first 10 chars = YYYY-MM-DD)
    try:
        dt = datetime.strptime(time_string[:10], "%Y-%m-%d")
        return dt.replace(hour=0, minute=0, second=0)
    except (ValueError, IndexError):
        pass

    return None


def read_events_from_csv(source_file: Path) -> list[dict]:
    """Read Shopify app events from a CSV file.

    Returns a list of plain dicts (one per row), sorted by time.
    Each dict has the raw CSV values keyed by header name.
    """
    rows: list[dict] = []

    with open(source_file, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))

    # Sort by Date field
    rows.sort(key=lambda r: parse_time_str(r.get("Date", ""), EVENT_TIME_PATTERN)
              or datetime.min)

    return rows


def read_pricing_def_from_json(source_file: Path) -> dict:
    """Read pricing definitions from a JSON file. Returns a plain dict."""
    with open(source_file, "r", encoding="utf-8") as f:
        return json.load(f)


def read_pricing_def_from_json_str(json_str: str) -> dict:
    """Read pricing definitions from a JSON string. Returns a plain dict."""
    return json.loads(json_str)


def read_excluding_def_from_json(source_file: Path) -> dict:
    """Read excluding definition from a JSON file. Returns a plain dict."""
    with open(source_file, "r", encoding="utf-8") as f:
        return json.load(f)


def read_excluding_def_from_json_str(json_str: str) -> dict:
    """Read excluding definition from a JSON string. Returns a plain dict."""
    return json.loads(json_str)


def write_json(file_out: Path, data: object) -> None:
    """Write data as pretty-printed JSON, creating parent dirs if needed."""
    file_out.parent.mkdir(parents=True, exist_ok=True)
    with open(file_out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
