#!/usr/bin/env python3
"""Strip identifying detail out of replay data before it is published.

The dashboard is useful precisely because it shows real runs, which means the
raw replay JSON carries real session ids, real repo paths, and real tool
arguments. None of that belongs on a public URL.

What survives: the shape of the finding - how many runs, how many stuck, which
signature fired, how far past the trip point the run continued. That is the part
that makes the case. The identifiers are noise to a reader and exposure to the
owner.

Session ids become short stable hashes so rows stay distinguishable across
renders without being traceable. Project names collapse to generic slugs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

# Only built-in, non-tenant tool labels are safe to expose. Transcript data can
# name arbitrary MCP servers or private tools, so syntax validation is not a
# privacy boundary. Arguments never appear in the dashboard.
PUBLIC_TOOL_NAMES = frozenset(
    (
        "Bash",
        "Edit",
        "Glob",
        "Grep",
        "Read",
        "Task",
        "WebFetch",
        "WebSearch",
        "Write",
    )
)
PUBLIC_RUN_ID = re.compile(r"^run-[0-9a-f]{7}$")
PUBLIC_REASONS = frozenset(("repeat", "alternation", "no_progress"))
PUBLIC_THRESHOLD_KEYS = (
    "repeat_threshold",
    "window",
    "no_progress_threshold",
    "alternation_threshold",
)


def short_hash(value: str, length: int = 7) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _safe_session_id(value: object) -> str:
    """Preserve only the sanitizer's prefixed generic public run-ID shape."""
    candidate = str(value)
    return candidate if PUBLIC_RUN_ID.fullmatch(candidate) else f"run-{short_hash(candidate)}"


def generic_project(name: str, mapping: dict[str, str]) -> str:
    if name not in mapping:
        mapping[name] = f"repo-{len(mapping) + 1}"
    return mapping[name]


def _safe_count(value: object, default: int = 0) -> int:
    """Keep public counts numeric and non-negative."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return value


def _safe_optional_count(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _safe_thresholds(value: object) -> dict[str, int | None]:
    """Copy only the numeric threshold fields used by replay_transcripts."""
    if not isinstance(value, dict):
        return {}
    clean: dict[str, int | None] = {}
    for key in PUBLIC_THRESHOLD_KEYS:
        threshold = value.get(key)
        if threshold is None:
            if key in value:
                clean[key] = None
        elif (isinstance(threshold, int) and not isinstance(threshold, bool)
              and threshold > 0):
            clean[key] = threshold
    return clean


def _safe_reason(value: object) -> str:
    if value == "":
        return ""
    if isinstance(value, str) and value in PUBLIC_REASONS:
        return value
    return "unknown"


def _safe_tool_name(detail: object) -> str:
    """Keep only known built-in labels, never transcript-controlled names."""
    if not isinstance(detail, str):
        return "unknown tool"
    candidate = detail.split(" called", 1)[0].strip()
    return candidate if candidate in PUBLIC_TOOL_NAMES else "unknown tool"


def _safe_detail(row: dict, reason: str) -> str:
    """Rebuild the small public detail vocabulary from untrusted input."""
    if reason == "":
        return ""
    if reason == "repeat":
        return f"{_safe_tool_name(row.get('detail'))} called with identical input"
    if reason == "alternation":
        return "two tools alternated without converging"
    if reason == "no_progress":
        return "consecutive calls mutated nothing"
    return "unclassified finding"


def sanitize(data: dict) -> dict:
    projects: dict[str, str] = {}
    out_results = []

    rows = data.get("results", [])
    if not isinstance(rows, list):
        rows = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        reason = _safe_reason(row.get("reason"))

        out_results.append(
            {
                "session": _safe_session_id(row.get("session", "")),
                "project": generic_project(str(row.get("project", "")), projects),
                "total_calls": _safe_count(row.get("total_calls")),
                "stuck": row.get("stuck") if isinstance(row.get("stuck"), bool) else False,
                "reason": reason,
                "detail": _safe_detail(row, reason),
                "fired_at_call": _safe_optional_count(row.get("fired_at_call")),
                "calls_after_trip": _safe_count(row.get("calls_after_trip")),
            }
        )

    with_calls = (
        len(out_results)
        if "with_calls" not in data
        else _safe_count(data.get("with_calls"))
    )

    return {
        "thresholds": _safe_thresholds(data.get("thresholds")),
        "scanned": _safe_count(data.get("scanned")),
        "with_calls": with_calls,
        "results": out_results,
        "sanitized": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="src", type=Path, required=True)
    parser.add_argument("--out", dest="dst", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.src.read_text(encoding="utf-8"))
    clean = sanitize(data)
    args.dst.parent.mkdir(parents=True, exist_ok=True)
    args.dst.write_text(json.dumps(clean, indent=2), encoding="utf-8")

    leaked = [t for t in ("Users", "patri", "autotrader", "bmdpat", "K--", "wsl")
              if t.lower() in json.dumps(clean).lower()]
    print(f"sanitized {len(clean['results'])} rows -> {args.dst}")
    print(f"projects collapsed: {len(set(r['project'] for r in clean['results']))}")
    if leaked:
        print(f"WARNING: possible identifiers still present: {leaked}")
        return 2
    print("no identifying tokens found in output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
