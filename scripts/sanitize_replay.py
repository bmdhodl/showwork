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

# Tool names are public API surface (everyone has Read/Bash/mcp__*), so they
# stay. Arguments never appear in the dashboard, but strip them defensively in
# case a future template starts rendering `detail` verbatim.
DETAIL_ARGS = re.compile(r"\s+with identical input.*$")


def short_hash(value: str, length: int = 7) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def generic_project(name: str, mapping: dict[str, str]) -> str:
    if name not in mapping:
        mapping[name] = f"repo-{len(mapping) + 1}"
    return mapping[name]


def sanitize(data: dict) -> dict:
    projects: dict[str, str] = {}
    out_results = []

    for row in data.get("results", []):
        detail = row.get("detail", "")
        # Keep the tool name and the count; drop the argument payload.
        detail = DETAIL_ARGS.sub(" with identical input", detail)

        out_results.append(
            {
                "session": short_hash(str(row.get("session", ""))),
                "project": generic_project(str(row.get("project", "")), projects),
                "total_calls": row.get("total_calls", 0),
                "stuck": bool(row.get("stuck")),
                "reason": row.get("reason", ""),
                "detail": detail,
                "fired_at_call": row.get("fired_at_call"),
                "calls_after_trip": row.get("calls_after_trip", 0),
            }
        )

    return {
        "thresholds": data.get("thresholds", {}),
        "scanned": data.get("scanned", 0),
        "with_calls": data.get("with_calls", 0),
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

    raw = args.src.read_text(encoding="utf-8")
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
