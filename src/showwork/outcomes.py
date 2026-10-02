"""Declared acceptance checks and complete, portable release receipts.

Requirements live in the existing session event stream. They are not inferred
from prose, and a passing command does not establish that its test is adequate.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


def requirement_records(root: Path, session: str) -> list[dict]:
    from .ledger import load_all_events
    return [row for row in load_all_events(root)
            if row.get("session") == session and row.get("event") == "session.requirement"]


def record_requirement(root: Path, session: str, requirement_id: str,
                       description: str, scope: str, check: dict) -> dict:
    from .checks import validate_check_shape
    from .ledger import _latest_session_start, claims_for_session, record_event
    if not _latest_session_start(root, session):
        raise ValueError("start the session before declaring requirements")
    if not isinstance(requirement_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", requirement_id):
        raise ValueError("requirement id must be 1-80 letters, digits, underscores or hyphens")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("requirement description must not be empty")
    if scope not in {"artifact", "behavior"}:
        raise ValueError("requirement scope must be artifact or behavior")
    error = validate_check_shape(check, root)
    if error:
        raise ValueError(error)
    if scope == "behavior" and check.get("type") != "command":
        raise ValueError("behavior requires an executable command check; file text is not behavior")
    if any(row.get("requirement_id") == requirement_id for row in requirement_records(root, session)):
        raise ValueError("requirement id already exists; acceptance checks cannot be weakened in place")
    if claims_for_session(root, session):
        raise ValueError("declare acceptance checks before recording completion claims")
    return record_event(root, "session.requirement", session,
                        requirement_id=requirement_id, claim=description,
                        scope=scope, check=check, severity="RED")


def evaluate_requirements(root: Path, session: str, *, allowed_check_types=None) -> list[dict]:
    return evaluate_requirement_records(root, requirement_records(root, session),
                                        allowed_check_types=allowed_check_types)


def evaluate_requirement_records(root: Path, records: list[dict], *,
                                 allowed_check_types=None, command_cache=None) -> list[dict]:
    """Evaluate loaded requirement events without rereading history per session."""
    from .checks import verify_claim
    rows = []
    seen = set()
    for record in records:
        session = record.get("session", "")
        requirement_id = record.get("requirement_id")
        error = None
        if not isinstance(session, str) or not session:
            error = "invalid requirement session"
        elif not isinstance(requirement_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", requirement_id):
            error = "invalid requirement id"
        elif (session, requirement_id) in seen:
            error = "duplicate requirement id; acceptance checks cannot be replaced"
        else:
            seen.add((session, requirement_id))
        scope, check = record.get("scope"), record.get("check")
        if scope not in ("artifact", "behavior") or not isinstance(check, dict):
            error = "requirement is missing its scope or executable check"
        elif scope == "behavior" and check.get("type") != "command":
            error = "behavior requires an executable command check"
        if error:
            rows.append({"claim": str(record.get("claim", "invalid requirement")),
                         "session": session, "requirement_id": requirement_id,
                         "type": "requirement", "severity": "RED", "status": "fail",
                         "detail": error})
        else:
            # Evaluate individually: claim retractions cannot erase requirements.
            clean = {k: record[k] for k in ("claim", "session", "check") if k in record}
            clean.update(requirement_id=requirement_id, scope=scope, severity="RED")
            rows.append(verify_claim(clean, root, allowed_check_types=allowed_check_types,
                                     acceptance_requirement=True, command_cache=command_cache))
    return rows


def outcome_summary(state: dict) -> dict:
    rows = [r for r in state["results"] if "requirement_id" in r]
    passed = sum(r["status"] == "pass" for r in rows)
    if not rows:
        verdict, reason = "UNVERIFIED", "No acceptance requirements declared. Only individual checks were evaluated."
    elif state["verdict"] != "GREEN" or passed != len(rows):
        verdict, reason = "UNVERIFIED", "Some acceptance checks or session checks did not pass."
    else:
        verdict, reason = "VERIFIED", "Declared acceptance checks passed; requirement coverage and test adequacy need review."
    return {"verdict": verdict, "passed": passed, "total": len(rows), "reason": reason,
            "scope": "declared requirements only", "undeclared_requirements": "unknown",
            "behavior_checks": sum(r.get("scope") == "behavior" for r in rows),
            "artifact_checks": sum(r.get("scope") == "artifact" for r in rows)}


def receipt_manifest(root: Path, session: str, *, include_recovery: bool = True) -> dict:
    from .ledger import iter_claim_paths, _read_jsonl
    # Ledger paths are canonicalized; normalize the root to the same spelling
    # before computing portable names (macOS /var and Windows short paths).
    root = root.resolve()
    files = {}
    for path in iter_claim_paths(root):
        if any(row.get("session") == session for row in _read_jsonl(path)):
            files[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    requirements = requirement_records(root, session)
    digest = hashlib.sha256(json.dumps(requirements, sort_keys=True,
                                      ensure_ascii=True).encode()).hexdigest()
    manifest = {"claims": files, "requirements_sha256": digest,
                "requirement_count": len(requirements)}
    if include_recovery:
        from .recovery import recovery_manifest
        manifest.update(recovery_manifest(root, session))
    return manifest


def release_gate(root: Path, session: str, *, require_tracked: bool = False,
                 legacy_integrity_baseline: str | None = None,
                 _allow_recovery: bool = True) -> dict:
    from .audit import audit_root
    from .ledger import load_all_events, session_events_path, session_file_stem, verify_session
    from .snapshot import snapshot_file
    from .ledger import ledger_dir, _read_jsonl
    root = root.resolve()
    errors = []
    # Commands are trusted project code, but their ledger mutations still need
    # to be audited. Auditing first left a gap after the last command ran.
    state = verify_session(root, session)
    audit = audit_root(root)
    baseline = None
    acknowledged = set()
    if legacy_integrity_baseline is not None:
        from .legacy import inspect_legacy_baseline
        baseline = inspect_legacy_baseline(root, session, legacy_integrity_baseline)
        errors.extend(baseline["errors"])
        if not baseline["errors"]:
            acknowledged = {row["path"] for row in baseline["acknowledged"]}
    # Historical pre-chain files do not certify this session, and must remain
    # visible. Any broken chain still fails, including unrelated history.
    for entry in audit["files"]:
        if entry["verdict"] == "RED" and f".showwork/{entry['file']}" not in acknowledged:
            errors.append(f"ledger integrity is RED: {entry['file']}")
        elif entry["verdict"] != "GREEN" and any(
                row.get("session") == session for row in _read_jsonl(Path(entry["path"]))):
            errors.append(f"selected session integrity is not GREEN: {entry['file']}")
    if state["verdict"] != "GREEN" or state["outcome"]["verdict"] != "VERIFIED":
        errors.append("declared acceptance checks are not verified")
        errors.extend(f"{r.get('requirement_id', r.get('claim', 'check'))}: {r['detail']}"
                      for r in state["results"] if r["status"] != "pass")
    events = [e for e in load_all_events(root) if e.get("session") == session]
    closes = [e for e in events if e.get("event") == "session.finish"]
    close = closes[-1] if closes else {}
    lifecycle = [e for e in events if e.get("event") in
                 {"session.start", "session.finish", "session.finish.refused"}]
    if not lifecycle or lifecycle[-1].get("event") != "session.finish":
        errors.append("the session is open or its latest close was refused")
    if (close.get("status") != "ok" or close.get("verify_bypassed")
            or close.get("completion_scope") != "outcome"):
        errors.append("no successful outcome close; checks-only and bypass closes do not qualify")
    manifest = receipt_manifest(root, session)
    if close.get("receipt_manifest") != manifest:
        errors.append("receipt manifest differs: missing, changed or unrecorded claim definitions")
    if require_tracked:
        paths = [*manifest["claims"],
                 session_events_path(root, session).relative_to(root).as_posix(),
                 snapshot_file(ledger_dir(root), session_file_stem(session)).relative_to(root).as_posix(),
                 *manifest.get("recovery_work", {})]
        for rel in paths:
            result = subprocess.run(["git", "-C", str(root), "show", f"HEAD:{rel}"],
                                    capture_output=True, timeout=15)
            path = root / rel
            if rel in manifest.get("recovery_work", {}) and manifest["recovery_work"][rel] is None:
                if result.returncode == 0 or path.exists():
                    errors.append(f"covered deletion is not committed exactly at HEAD: {rel}")
                continue
            if (result.returncode or not path.is_file()
                    or result.stdout.replace(b"\r\n", b"\n") != path.read_bytes().replace(b"\r\n", b"\n")):
                errors.append(f"receipt is not committed exactly at HEAD: {rel}")
    result = {"verdict": "RED" if errors else "GREEN", "session": session,
            "errors": errors, "checks": state, "historical_integrity": audit["verdict"],
            "legacy_baseline": baseline,
            "integrity_scope": ("selected session; pinned legacy history remains unverified"
                                if baseline else "selected session; unrelated RED findings still fail")}
    from .recovery import incoming_recovery, _validate, _evidence, canonical_bytes
    incoming = incoming_recovery(root, session)
    if incoming and _allow_recovery:
        try:
            if len(incoming) != 1:
                raise ValueError("ambiguous recovery links")
            recovery = incoming[0]
            replacement = recovery["session"]
            _validate(root, replacement, recovery, claims_required=True)
            fresh = release_gate(root, replacement, require_tracked=require_tracked,
                                 legacy_integrity_baseline=legacy_integrity_baseline,
                                 _allow_recovery=False)
            # Acceptance commands must not mutate preserved history.
            _validate(root, replacement, recovery, claims_required=True)
            if require_tracked:
                for rel in _evidence(root, session):
                    committed = subprocess.run(["git", "-C", str(root), "show", f"HEAD:{rel}"],
                                               capture_output=True, timeout=15)
                    if (committed.returncode or canonical_bytes(committed.stdout)
                            != canonical_bytes((root / rel).read_bytes())):
                        raise ValueError(f"superseded evidence is not committed exactly at HEAD: {rel}")
            if fresh["verdict"] != "GREEN":
                raise ValueError("replacement outcome is not verified: " + "; ".join(fresh["errors"]))
            result.update(verdict="GREEN", errors=[], original_errors=errors,
                          recovery={"replacement": replacement, "original_outcome": state["outcome"],
                                    "reason": recovery["reason"], "coverage": recovery["coverage"],
                                    "replacement_gate": fresh})
        except (ValueError, OSError, TypeError, KeyError) as exc:
            result["errors"].append(f"recovery rejected: {exc}")
            result["verdict"] = "RED"
    return result


def changed_sessions(root: Path, base: str) -> list[str]:
    """Select receipts since the fork point, including deleted claim files."""
    from .ledger import load_all_events, session_file_stem
    if not base or base.startswith("-"):
        raise ValueError("changed-since must be a Git revision")
    # Comparing branch tips treats receipts added only on main as PR deletions.
    # Use the same fork-point comparison as a pull request's Files changed view.
    merge_base = subprocess.run(
        ["git", "-C", str(root), "merge-base", base, "HEAD"],
        capture_output=True, text=True, timeout=15)
    if merge_base.returncode:
        raise ValueError("cannot resolve a common receipt base; fetch both revisions "
                         "and use actions/checkout with fetch-depth: 0")
    base = merge_base.stdout.strip()
    diff = subprocess.run(["git", "-C", str(root), "diff", "--no-renames", "--name-only", base, "HEAD",
                           "--", ".showwork/"], capture_output=True, text=True, timeout=15)
    if diff.returncode:
        raise ValueError("cannot resolve changed receipt paths")
    paths = set(diff.stdout.splitlines())
    sessions = set()
    events = load_all_events(root)
    # Read baseline IDs too: deleting a bad receipt must not hide it behind a new one.
    for rel in paths:
        if rel.startswith(".showwork/sessions/") and rel.endswith(".jsonl"):
            previous = subprocess.run(["git", "-C", str(root), "show", f"{base}:{rel}"],
                                      capture_output=True, text=True, timeout=15)
            if previous.returncode == 0:
                for line in previous.stdout.splitlines():
                    if line.strip() and not line.lstrip().startswith("#"):
                        row = json.loads(line)
                        if isinstance(row, dict):
                            events.append(row)
    for event in events:
        session = event.get("session")
        if not isinstance(session, str) or not session:
            continue
        stem = session_file_stem(session)
        if any(p in paths for p in (f".showwork/sessions/{stem}.jsonl",
                                   f".showwork/claims/{stem}.jsonl",
                                   f".showwork/snapshots/{stem}.json")):
            sessions.add(session)
    if not sessions:
        raise ValueError("no changed session receipt found; this change has no outcome close")
    return sorted(sessions)


def runtime_identity() -> dict:
    import importlib.metadata
    import sys
    from . import __version__
    try:
        installed = importlib.metadata.version("showwork")
    except importlib.metadata.PackageNotFoundError:
        installed = None
    return {"runtime_version": __version__, "distribution_version": installed,
            "module": str(Path(__file__).resolve()), "python": sys.executable,
            "consistent": installed == __version__}
