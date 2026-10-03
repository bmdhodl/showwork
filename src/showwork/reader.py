"""Bounded, process-free receipt inspection. Historical evidence is not a rerun."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .audit import audit_file
from .ledger import split_record_lines, _reject_nonfinite

MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_LEDGER_FILES = 1024
VERSIONS = tuple(f"spec-v0.{i}" for i in range(1, 6))
EVENTS = frozenset({"session.start", "session.requirement", "session.finish",
                    "session.finish.refused"})
CHECK_TYPES = frozenset({"file_exists", "file_contains", "path_moved", "frontmatter",
                         "glob_count", "command", "http_probe", "git_state"})
CAPABILITIES = {
    "spec_versions": list(VERSIONS), "integrity": "hash-chain",
    "scope": "recorded requirements and receipt manifest",
    "current_execution": "not performed", "processes": False, "network": False,
    "test_adequacy": "not assessed", "origin_authentication": "not established",
}


def confined_path(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("receipt path escapes workspace")
    return resolved


def read_bytes(root: Path, path: Path) -> bytes:
    path = confined_path(root, path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("receipt exceeds reader size limit")
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("receipt exceeds reader size limit")
    return data


def load_receipt(root: Path, session: str) -> dict:
    """Read existing layouts without Git discovery or following escaping links."""
    root = root.resolve()
    if not root.is_dir() or not isinstance(session, str) or not session.strip():
        raise ValueError("workspace or session missing")
    base = confined_path(root, root / ".showwork")
    if not base.is_dir():
        return {"claims": [], "events": [], "files": {}, "audit": []}
    paths = sorted(base.glob("claims-*.jsonl"))
    legacy = base / "sessions.jsonl"
    if legacy.exists():
        paths.append(legacy)
    for folder in (base / "claims", base / "sessions"):
        confined_path(root, folder)
        if folder.is_dir():
            paths.extend(sorted(folder.glob("*.jsonl")))
    if len(paths) > MAX_LEDGER_FILES:
        raise ValueError("too many receipt files for bounded reader")
    claims, events, files, audits = [], [], {}, []
    total = 0
    for path in paths:
        data = read_bytes(root, path)
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("receipts exceed reader total size limit")
        text = data.decode("utf-8-sig")
        rows = []
        for line in split_record_lines(text):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line, parse_constant=_reject_nonfinite,
                             object_pairs_hook=_unique_object)
            if not isinstance(row, dict):
                raise ValueError("non-object ledger record")
            rows.append(row)
        audits.append(audit_file(path, record_text=text))
        selected = [row for row in rows if row.get("session") == session or
                    isinstance(row.get("retracts"), dict) and
                    row["retracts"].get("session") == session]
        if path.parent.name == "sessions" or path.name == "sessions.jsonl":
            events.extend(selected)
        else:
            claims.extend(selected)
            if selected:
                files[path.relative_to(root).as_posix()] = hashlib.sha256(
                    data.replace(b"\r\n", b"\n")).hexdigest()
    events.sort(key=lambda row: str(row.get("ts", "")))
    return {"claims": claims, "events": events, "files": files, "audit": audits}


def inspect_loaded(receipt: dict) -> dict:
    """Shared reader labels; no current behavior check is implied."""
    events, claims = receipt["events"], receipt["claims"]
    audits = receipt["audit"]
    integrity = ("RED" if any(row["verdict"] == "RED" for row in audits) else
                 "YELLOW" if not audits or any(row["verdict"] != "GREEN" for row in audits)
                 else "GREEN")
    unsupported = any(
        row.get("spec_version") not in (None, *VERSIONS) or
        bool(row.get("required_semantics")) or
        row.get("event") not in EVENTS
        for row in events
    ) or any(row.get("spec_version") not in (None, *VERSIONS) or
             bool(row.get("required_semantics")) for row in claims)
    requirements = [row for row in events if row.get("event") == "session.requirement"]
    if any(not isinstance(row.get("check"), dict) or
           row["check"].get("type") not in CHECK_TYPES or
           row.get("scope") not in {"behavior", "artifact"} or
           row.get("scope") == "behavior" and row["check"].get("type") != "command"
           for row in requirements):
        unsupported = True
    if any(isinstance(row.get("check"), dict) and row["check"].get("type") not in CHECK_TYPES
           for row in claims):
        unsupported = True
    lifecycle = [row for row in events if row.get("event") in
                 {"session.start", "session.finish", "session.finish.refused"}]
    latest = lifecycle[-1] if lifecycle else {}
    closes = [row for row in lifecycle if row.get("event") == "session.finish"]
    close = closes[-1] if closes else {}
    expected = {
        "claims": receipt["files"], "requirement_count": len(requirements),
        "requirements_sha256": hashlib.sha256(json.dumps(
            requirements, sort_keys=True, ensure_ascii=True).encode()).hexdigest(),
    }
    manifest = "absent" if "receipt_manifest" not in close else (
        "matches" if close["receipt_manifest"] == expected else "mismatch")
    historical = "absent"
    if latest.get("event") == "session.finish.refused":
        historical = "refused"
    elif close:
        outcome = close.get("outcome")
        historical = str(outcome.get("verdict", "unverified")) if isinstance(outcome, dict) else "unverified"
    freshness = "reopened" if close and latest.get("event") == "session.start" else (
        "recorded_close" if latest.get("event") == "session.finish" else "open_or_absent")
    qualified = (not unsupported and integrity == "GREEN" and manifest == "matches"
                 and freshness == "recorded_close" and close.get("status") == "ok"
                 and close.get("completion_scope") == "outcome"
                 and not close.get("verify_bypassed") and historical == "VERIFIED")
    return {
        "integrity": integrity, "scope": CAPABILITIES["scope"],
        "spec_coverage": "unsupported" if unsupported else "supported_reading_fields",
        "manifest": manifest, "freshness": freshness,
        "historical_outcome": historical,
        "recorded_outcome": "VERIFIED" if qualified else "UNVERIFIED",
        "current_execution": "not performed", "current_outcome": "UNVERIFIED",
        "requirement_count": len(requirements),
        "capabilities": {**CAPABILITIES, "spec_versions": list(VERSIONS)},
    }


def _unique_object(pairs: list[tuple]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def inspect_session(root: str | Path, session: str) -> dict:
    """Inspect a named receipt; unknown input never becomes verified evidence."""
    try:
        return inspect_loaded(load_receipt(Path(root), session))
    except (OSError, ValueError, TypeError, AttributeError):
        result = inspect_loaded({"claims": [], "events": [], "files": {}, "audit": []})
        result.update(integrity="unknown", spec_coverage="unreadable",
                      reason="receipt unreadable or outside reader bounds")
        return result
