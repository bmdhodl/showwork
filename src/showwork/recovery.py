"""Append-only recovery of a missing-acceptance ordering error.

The failed attempt stays failed. Only a separately verified replacement can
certify its work. Existing acceptance requirements cannot be superseded.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def recovery_records(root: Path, session: str) -> list[dict]:
    from .ledger import load_all_events
    return [e for e in load_all_events(root)
            if e.get("session") == session and e.get("event") == "session.recovery"]


def canonical_bytes(raw: bytes) -> bytes:
    # Match Git checkout conversion, without changing binary evidence.
    try:
        raw.decode("utf-8")
        if b"\x00" not in raw:
            raw = raw.replace(b"\r\n", b"\n")
    except UnicodeDecodeError:
        pass
    return raw


def _digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"recovery evidence is missing or linked: {path.name}")
    return hashlib.sha256(canonical_bytes(path.read_bytes())).hexdigest()


def _events(root: Path, session: str) -> list[dict]:
    from .ledger import load_all_events
    return [e for e in load_all_events(root) if e.get("session") == session]


def _evidence(root: Path, session: str) -> dict[str, str]:
    from .ledger import (iter_claim_paths, iter_session_event_paths, _read_jsonl,
                         ledger_dir, session_file_stem, session_artifacts_dir)
    from .snapshot import snapshot_file
    paths = [p for p in [*iter_claim_paths(root), *iter_session_event_paths(root)]
             if any(e.get("session") == session for e in _read_jsonl(p))]
    paths.append(snapshot_file(ledger_dir(root), session_file_stem(session)))
    artifacts = session_artifacts_dir(root, session)
    if artifacts.is_dir():
        paths += [p for p in artifacts.rglob("*") if p.is_file() or p.is_symlink()]
    return {p.relative_to(root).as_posix(): _digest(p) for p in paths}


def _work(root: Path, session: str) -> set[str]:
    from .ledger import claims_for_session, ledger_dir, session_file_stem
    from .snapshot import (snapshot_file, capture_tree, declared_paths, _files_digest,
                           _git_line_endings_only, _in_skipped_dir, SKIP_FILES,
                           SKIP_SUFFIXES)
    starts = [e for e in _events(root, session) if e.get("event") == "session.start"]
    if not starts:
        raise ValueError("superseded session has no start")
    meta = starts[-1].get("tree_snapshot")
    payload = json.loads(snapshot_file(ledger_dir(root), session_file_stem(session)).read_text())
    files = payload.get("files")
    if (not isinstance(meta, dict) or not isinstance(files, dict)
            or _files_digest(files) != meta.get("sha256")):
        raise ValueError("superseded snapshot does not match its chained start")
    current = capture_tree(root)
    changed = {p for p in current if p not in files}
    for p, digest in files.items():
        if (_in_skipped_dir(p) or Path(p).name in SKIP_FILES
                or p.endswith(SKIP_SUFFIXES) or p.endswith("~")):
            continue
        if p not in current or (current[p] != digest
                               and not _git_line_endings_only(root / p, digest)):
            changed.add(p)
    claims = claims_for_session(root, session)
    # Command arguments such as "python" are not work paths.
    changed |= {p for p in declared_paths(claims, root)
                if p in files or p in current or (root / p).is_file()}
    # Deleted paths must still be explicitly covered.
    for claim in claims:
        check = claim.get("check") or {}
        for key in ("path", "from", "to"):
            p = check.get(key)
            if isinstance(p, str):
                resolved = (root / p).resolve()
                if not resolved.is_relative_to(root):
                    raise ValueError("superseded work path escapes project")
                changed.add(resolved.relative_to(root).as_posix())
    return changed


def _validate(root: Path, session: str, event: dict, *, claims_required: bool) -> set[str]:
    from .audit import audit_root
    from .ledger import claims_for_session, load_all_events
    from .outcomes import requirement_records, receipt_manifest
    from .snapshot import declared_paths
    old = event.get("supersedes")
    if not isinstance(old, str) or not old or old == session:
        raise ValueError("invalid or self-referential recovery link")
    before = _events(root, old)
    lifecycle = [e for e in before if e.get("event") in
                 {"session.start", "session.finish", "session.finish.refused"}]
    if (not lifecycle or lifecycle[-1].get("event") != "session.finish"
            or lifecycle[-1].get("status") != "blocked"
            or lifecycle[-1].get("verify_bypassed")
            or (lifecycle[-1].get("outcome") or {}).get("verdict") != "UNVERIFIED"):
        raise ValueError("superseded attempt must have a non-bypassed blocked close")
    if any(e.get("event") == "session.finish" and e.get("status") == "ok" for e in before):
        raise ValueError("a previously successful session cannot be superseded")
    if requirement_records(root, old) or recovery_records(root, old):
        raise ValueError("existing requirements or recovery chains cannot be superseded")
    if not any(e.get("refuse_reason") == "acceptance_requirements_unverified" for e in before):
        raise ValueError("recovery requires a recorded missing-acceptance refusal")
    incoming = [e for e in load_all_events(root) if e.get("event") == "session.recovery"
                and e.get("supersedes") == old]
    if incoming and (len(incoming) != 1 or incoming[0].get("session") != session):
        raise ValueError("ambiguous recovery links")
    if incoming_recovery(root, session):
        raise ValueError("recovery chains cannot target a replacement")
    own = _events(root, session)
    starts = [e for e in own if e.get("event") == "session.start"]
    if len(starts) != 1 or starts[0].get("ts", "") < lifecycle[-1].get("ts", ""):
        raise ValueError("replacement must be a fresh session started after the blocked close")
    requirements = requirement_records(root, session)
    behaviors = {e["requirement_id"] for e in requirements
                 if e.get("scope") == "behavior" and (e.get("check") or {}).get("type") == "command"}
    if not behaviors or receipt_manifest(root, session, include_recovery=False)["requirements_sha256"] != event.get("requirements_sha256"):
        raise ValueError("fresh executable requirements are missing or changed")
    claims = claims_for_session(root, session)
    if any(e.get("ts", "") > min((c.get("ts", "") for c in claims), default="9999")
           for e in [*requirements, event]):
        raise ValueError("recovery and requirements must precede completion claims")
    coverage = event.get("coverage")
    if (not isinstance(coverage, dict) or not coverage
            or any(not isinstance(p, str) or not p or r not in behaviors
                   for p, r in coverage.items())):
        raise ValueError("coverage must map work paths to fresh behavior requirement IDs")
    for p in coverage:
        if (root / p).resolve().relative_to(root).as_posix() != p or (root / p).is_symlink():
            raise ValueError("coverage paths must be canonical project-relative paths")
    needed = _work(root, old)
    missing = needed - coverage.keys()
    if missing:
        raise ValueError("missing recovery coverage: " + ", ".join(sorted(missing)))
    if claims_required:
        missing = coverage.keys() - declared_paths(claims, root)
        if missing:
            raise ValueError("fresh claims must name covered paths: " + ", ".join(sorted(missing)))
    evidence = _evidence(root, old)
    if evidence != event.get("evidence"):
        raise ValueError("superseded evidence changed after recovery declaration")
    for entry in audit_root(root)["files"]:
        if f".showwork/{entry['file']}" in evidence and entry["verdict"] != "GREEN":
            raise ValueError("superseded ledger integrity is not GREEN")
    return set(coverage)


def record_recovery(root: Path, session: str, supersedes: str, reason: str, coverage: dict) -> dict:
    from .ledger import claims_for_session, record_event
    from .outcomes import receipt_manifest
    root = root.resolve()
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("recovery needs a reason")
    if claims_for_session(root, session) or recovery_records(root, session):
        raise ValueError("declare recovery once, before completion claims")
    if any(e.get("event") in {"session.finish", "session.finish.refused"} for e in _events(root, session)):
        raise ValueError("replacement has already attempted a close")
    from .ledger import _now
    event = {"session": session, "ts": _now(), "supersedes": supersedes,
             "reason": reason, "coverage": coverage, "evidence": _evidence(root, supersedes),
             "requirements_sha256": receipt_manifest(root, session, include_recovery=False)["requirements_sha256"]}
    _validate(root, session, event, claims_required=False)
    return record_event(root, "session.recovery", session,
                        **{k: v for k, v in event.items() if k not in {"session", "ts"}})


def recovery_results(root: Path, session: str) -> list[dict]:
    records = recovery_records(root, session)
    if not records:
        return []
    try:
        if len(records) != 1:
            raise ValueError("replacement must have exactly one recovery declaration")
        _validate(root.resolve(), session, records[0], claims_required=True)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        return [{"claim": "recovery coverage and preserved history", "session": session,
                 "severity": "RED", "type": "recovery", "status": "fail",
                 "detail": str(exc), "synthetic": True}]
    return []


def recovery_manifest(root: Path, session: str) -> dict:
    records = recovery_records(root, session)
    if not records:
        return {}
    coverage = records[-1].get("coverage")
    work = {}
    # Malformed events still reach verification as RED; manifest construction
    # must neither crash nor open an author-supplied path outside the project.
    if isinstance(coverage, dict):
        for p in coverage:
            try:
                if not isinstance(p, str) or (root / p).resolve().relative_to(root).as_posix() != p:
                    continue
                work[p] = _digest(root / p) if (root / p).exists() else None
            except (ValueError, OSError):
                work[p] = "invalid evidence"
    return {"recovery_sha256": hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(),
            "recovery_work": work}


def incoming_recovery(root: Path, session: str) -> list[dict]:
    from .ledger import load_all_events
    return [e for e in load_all_events(root) if e.get("event") == "session.recovery"
            and e.get("supersedes") == session]
