#!/usr/bin/env python3
"""Strip identifying detail out of replay data before it is published.

The dashboard is useful precisely because it shows real runs, which means the
raw replay JSON carries real session ids, real repo paths, and real tool
arguments. None of that belongs on a public URL.

What survives: the shape of the finding - how many runs, how many stuck, which
signature fired, how far past the trip point the run continued. That is the part
that makes the case. The identifiers are noise to a reader and exposure to the
owner.

Session ids become opaque stable hashes so rows stay distinguishable across
renders without being traceable. Project names collapse to generic slugs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping
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
PUBLIC_REASONS = frozenset(("repeat", "alternation", "no_progress"))
PUBLIC_THRESHOLD_KEYS = (
    "repeat_threshold",
    "window",
    "no_progress_threshold",
    "alternation_threshold",
)


def _make_sanitized_types():
    capability = object()

    class SanitizedMapping(tuple, Mapping[str, object]):
        """Immutable mapping whose items live in the tuple payload."""

        __slots__ = ()

        def __new__(cls, items: Iterable[tuple[str, object]], _capability=None):
            if _capability is not capability:
                raise TypeError("sanitized replay mappings are internal only")
            return tuple.__new__(cls, tuple(items))

        def __getitem__(self, key: str) -> object:
            for item_key, value in tuple.__iter__(self):
                if item_key == key:
                    return value
            raise KeyError(key)

        def __iter__(self):
            return (key for key, _ in tuple.__iter__(self))

        def __len__(self) -> int:
            return tuple.__len__(self)

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Mapping):
                return NotImplemented
            return dict(self.items()) == dict(other.items())

    class SanitizedReplay(SanitizedMapping):
        """Private provenance marker for sanitizer output kept in memory."""

        __slots__ = ()

    def make_mapping(items: Iterable[tuple[str, object]]):
        return SanitizedMapping(items, capability)

    def make_replay(items: Iterable[tuple[str, object]]):
        return SanitizedReplay(items, capability)

    return SanitizedMapping, SanitizedReplay, make_mapping, make_replay


_SanitizedMapping, _SanitizedReplay, _new_sanitized_mapping, _new_sanitized_replay = (
    _make_sanitized_types()
)


def _to_jsonable(value: object) -> object:
    if isinstance(value, _SanitizedMapping):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return value


def short_hash(value: str, length: int = 7) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _safe_session_id(value: object) -> str:
    """Hash every transcript-controlled session id at the trust boundary."""
    return f"run-{short_hash(str(value))}"


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


def _safe_with_calls(value: object, fallback: int) -> int:
    """Keep counts usable for rates without trusting malformed input."""
    if (isinstance(value, bool) or not isinstance(value, int)
            or value != fallback):
        return fallback
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
    if isinstance(data, _SanitizedReplay):
        return data

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
            _new_sanitized_mapping(
                (
                    ("session", _safe_session_id(row.get("session", ""))),
                    ("project", generic_project(str(row.get("project", "")), projects)),
                    ("total_calls", _safe_count(row.get("total_calls"))),
                    ("stuck", row.get("stuck") if isinstance(row.get("stuck"), bool) else False),
                    ("reason", reason),
                    ("detail", _safe_detail(row, reason)),
                    ("fired_at_call", _safe_optional_count(row.get("fired_at_call"))),
                    ("calls_after_trip", _safe_count(row.get("calls_after_trip"))),
                )
            )
        )

    with_calls = _safe_with_calls(data.get("with_calls"), len(out_results))
    scanned = max(_safe_count(data.get("scanned")), with_calls)

    return _new_sanitized_replay(
        (
            ("thresholds", _new_sanitized_mapping(_safe_thresholds(data.get("thresholds")).items())),
            ("scanned", scanned),
            ("with_calls", with_calls),
            ("results", tuple(out_results)),
            ("sanitized", True),
        )
    )


def sanitize_for_public(data: object) -> Mapping[str, object]:
    """Sanitize at the renderer boundary without trusting provenance types."""
    if isinstance(data, _SanitizedMapping):
        data = _to_jsonable(data)
    if not isinstance(data, dict):
        data = {}
    return sanitize(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="src", type=Path, required=True)
    parser.add_argument("--out", dest="dst", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.src.read_text(encoding="utf-8"))
    clean = sanitize(data)
    clean_json = _to_jsonable(clean)
    args.dst.parent.mkdir(parents=True, exist_ok=True)
    args.dst.write_text(json.dumps(clean_json, indent=2), encoding="utf-8")

    leaked = [t for t in ("Users", "patri", "autotrader", "bmdpat", "K--", "wsl")
              if t.lower() in json.dumps(clean_json).lower()]
    print(f"sanitized {len(clean['results'])} rows -> {args.dst}")
    print(f"projects collapsed: {len(set(r['project'] for r in clean['results']))}")
    if leaked:
        print(f"WARNING: possible identifiers still present: {leaked}")
        return 2
    print("no identifying tokens found in output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
