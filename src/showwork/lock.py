"""Locked acceptance checks.

`showwork lock` freezes a session's declared requirements and the files that
define them: the script of every command requirement plus any explicitly named
relative globs. Verification refuses a clean close when any of them changed
after the lock. The lock is one record in the hash-chained session events file.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from .snapshot import (
    _git_line_endings_only,
    _hash_file,
    _rel_under_root,
    capture_tree,
    ignored_path,
    validate_ignore_patterns,
)

LOCK_EVENT = "session.lock"
LOCK_FORMAT = "showwork-lock-v1"
_DIGEST = re.compile(r"[0-9a-f]{64}")


def requirements_digest(requirements: list[dict]) -> str:
    return hashlib.sha256(json.dumps(requirements, sort_keys=True,
                                     ensure_ascii=True).encode()).hexdigest()


def _matches(rel: str, patterns: list[str]) -> bool:
    return any(ignored_path(rel, [p]) for p in patterns)


def lock_targets(root: Path, requirements: list[dict], patterns: list[str]) -> dict[str, str]:
    """SHA-256 of each command requirement's script and each file a pattern matches."""
    root = root.resolve()
    files: dict[str, str] = {}
    for row in requirements:
        check = row.get("check") or {}
        argv = check.get("argv") if check.get("type") == "command" else None
        if not isinstance(argv, list) or len(argv) < 2:
            continue
        rel = _rel_under_root(root, argv[1])
        digest = _hash_file(root / rel) if rel and (root / rel).is_file() else None
        if digest is None:
            raise ValueError(f"command script {argv[1]!r} of requirement "
                             f"{row.get('requirement_id')!r} is not a file to lock")
        files[rel] = digest
    if patterns:
        tree = capture_tree(root)
        for pattern in patterns:
            matched = {rel: digest for rel, digest in tree.items() if ignored_path(rel, [pattern])}
            if not matched:
                raise ValueError(f"lock path {pattern!r} matches no file")
            files.update(matched)
    return dict(sorted(files.items()))


def record_lock(root: Path, session: str, patterns: list[str] | None = None) -> dict:
    from .ledger import _latest_session_start, claims_for_session, load_all_events, record_event
    from .outcomes import requirement_records
    if not _latest_session_start(root, session):
        raise ValueError("start the session before locking its checks")
    if any(e.get("session") == session and e.get("event") == LOCK_EVENT
           for e in load_all_events(root)):
        raise ValueError("this session's checks are already locked; use a new session to change them")
    requirements = requirement_records(root, session)
    if not requirements:
        raise ValueError("declare acceptance requirements before locking them")
    if claims_for_session(root, session):
        raise ValueError("lock the checks before recording completion claims")
    patterns = validate_ignore_patterns(patterns, label="lock --path")
    files = lock_targets(root, requirements, patterns)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", "HEAD"],
                          capture_output=True, text=True, timeout=15)
    return record_event(
        root, LOCK_EVENT, session, lock_format=LOCK_FORMAT,
        requirement_ids=[row.get("requirement_id") for row in requirements],
        requirements_sha256=requirements_digest(requirements),
        lock_patterns=patterns, locked_files=files,
        git_commit=head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else None)


def _lock_error(lock: dict) -> str | None:
    files = lock.get("locked_files")
    patterns = lock.get("lock_patterns")
    ids = lock.get("requirement_ids")
    if lock.get("lock_format") != LOCK_FORMAT:
        return "unsupported lock format"
    if not isinstance(lock.get("requirements_sha256"), str) or not _DIGEST.fullmatch(lock["requirements_sha256"]):
        return "requirements_sha256 is missing or malformed"
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        return "requirement_ids must be a list of strings"
    if not isinstance(files, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and _DIGEST.fullmatch(v) for k, v in files.items()):
        return "locked_files must map paths to SHA-256 digests"
    try:
        if not isinstance(patterns, list) or validate_ignore_patterns(patterns, label="lock path") != patterns:
            return "lock_patterns are not canonical"
    except ValueError as exc:
        return str(exc)
    return None


def _row(claim: str, status: str, detail: str) -> dict:
    return {"claim": claim, "session": "", "severity": "RED", "type": "locked_check",
            "status": status, "detail": detail, "synthetic": True}


def lock_results(root: Path, events: list[dict], requirements: list[dict]) -> tuple[list[dict], dict | None]:
    """Rows for the verdict plus a summary for the finish record; ([], None) when unlocked."""
    locks = [e for e in events if e.get("event") == LOCK_EVENT]
    if not locks:
        return [], None
    if len(locks) > 1:
        detail = "the session holds more than one lock record; a lock cannot be replaced"
        return [_row("locked checks", "fail", detail)], {"status": "invalid", "findings": [detail]}
    lock = locks[0]
    problem = _lock_error(lock)
    if problem:
        detail = f"lock record is invalid: {problem}"
        return [_row("locked checks", "fail", detail)], {"status": "invalid", "findings": [detail]}
    root = root.resolve()
    findings = []
    if requirements_digest(requirements) != lock["requirements_sha256"]:
        current = [str(r.get("requirement_id")) for r in requirements]
        added = [i for i in current if i not in lock["requirement_ids"]]
        missing = [i for i in lock["requirement_ids"] if i not in current]
        findings += [f"requirement declared after the lock: {i}" for i in added]
        findings += [f"locked requirement is missing: {i}" for i in missing]
        if not added and not missing:
            findings.append("locked requirement records changed")
    for rel, digest in lock["locked_files"].items():
        path = root / rel
        if _rel_under_root(root, rel) != rel or path.is_symlink() or not path.is_file():
            findings.append(f"locked check file deleted: {rel}")
        elif _hash_file(path) != digest and not _git_line_endings_only(path, digest):
            findings.append(f"locked check file changed: {rel}")
    if lock["lock_patterns"]:
        findings += [f"new file under a locked path: {rel}" for rel in capture_tree(root)
                     if rel not in lock["locked_files"] and _matches(rel, lock["lock_patterns"])]
    summary = {"status": "changed" if findings else "intact",
               "requirements_sha256": lock["requirements_sha256"],
               "requirements": len(lock["requirement_ids"]),
               "files": len(lock["locked_files"]), "findings": findings}
    if findings:
        return [_row("locked checks", "fail", f) for f in findings], summary
    return [_row("locked checks", "pass",
                 f"{summary['requirements']} requirements and {summary['files']} files "
                 "match the lock")], summary
