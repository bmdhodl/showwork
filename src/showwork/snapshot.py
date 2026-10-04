"""Session-start tree snapshot and undeclared-change detection.

Issue #64: verify stayed GREEN when a file no claim named was deleted.
Claims only cover what the agent declared. A start snapshot is prior state
the ledger can compare at verify/finish time.

Old sessions with no tree_snapshot on session.start skip this check.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
from pathlib import Path

from .checks import apply_append_retractions, gaps_payload

# Generated output is outside the source snapshot. A build or a browser run rewrites
# thousands of files under these directories, and a session that ran one
# would drown in "undeclared change" gaps that name nothing a person wrote.
SKIP_DIRS = frozenset({
    ".showwork",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".tox",
    "htmlcov",
    "coverage",
    ".eggs",
    ".idea",
    ".vs",
    # web framework build output
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".turbo",
    ".cache",
    ".parcel-cache",
    ".vercel",
    # browser test output
    "test-results",
    "playwright-report",
    ".playwright",
    ".playwright-cli",
})
SKIP_FILES = frozenset({
    ".git",  # Worktrees use a pointer file where ordinary clones use a directory.
    ".env.local",  # Machine-local configuration is absent from CI checkouts.
    ".coverage",
    "next-env.d.ts",  # Next regenerates this file during dev, build and typegen.
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
})
SKIP_SUFFIXES = (".pyc", ".pyo", ".swp", ".swo", ".log", ".tsbuildinfo")
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_FILES = 50_000
IGNORE_FORMAT = "relative-glob-v1"
IGNORE_SEMANTIC = "snapshot-exclusions-v1"
MAX_IGNORE_PATTERNS = 32
MAX_IGNORE_LENGTH = 240
MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024
# One row per dead artifact is a nudge; a thousand is a wall of noise.
MAX_UNREFERENCED_ARTIFACTS = 100


def snapshot_file(ledger: Path, stem: str) -> Path:
    base = ledger.resolve()
    path = (base / "snapshots" / f"{stem}.json").resolve()
    if not path.is_relative_to(base):
        raise ValueError("snapshot path escapes the ledger")
    return path


def validate_ignore_patterns(ignore: list[str] | None) -> list[str]:
    """Canonical, bounded POSIX component globs; no implicit Git ignore rules."""
    if ignore is None:
        return []
    if not isinstance(ignore, list) or len(ignore) > MAX_IGNORE_PATTERNS:
        raise ValueError("ignore must be a list of at most 32 relative globs")
    for pattern in ignore:
        if (not isinstance(pattern, str) or not 1 <= len(pattern) <= MAX_IGNORE_LENGTH
                or any(ord(c) < 32 or ord(c) == 127 for c in pattern)
                or any(c in pattern for c in "\\:[]")):
            raise ValueError("ignore requires a bounded slash-separated relative glob")
        parts = pattern.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise ValueError("ignore cannot be absolute, empty or traverse parents")
        if any("**" in part and not (part == "**" and i == len(parts) - 1)
               for i, part in enumerate(parts)) or parts == ["**"]:
            raise ValueError("ignore supports ** only as a terminal recursive component")
        # A wildcard prefix must not cover the protected ledger or Git state.
        if any(fnmatch.fnmatchcase(name, part.casefold()) for part in parts if part != "**"
               for name in (".git", ".showwork")):
            raise ValueError("ignore cannot target .git, .showwork or the whole workspace")
    return sorted(set(ignore))


def ignored_path(relative: str, ignore: list[str], *, directory: bool = False) -> bool:
    parts = relative.split("/")
    for pattern in ignore:
        wanted = pattern.split("/")
        recursive = wanted[-1] == "**"
        prefix = wanted[:-1] if recursive else wanted
        if ((recursive and len(parts) >= len(prefix) or not recursive and len(parts) == len(prefix))
                and (not directory or recursive)
                and all(fnmatch.fnmatchcase(part, glob) for part, glob in zip(parts, prefix))):
            return True
    return False


def capture_tree(root: Path, *, ignore: list[str] | None = None) -> dict[str, str]:
    """Map posix-relative paths to SHA-256 hex of file bytes."""
    root = root.resolve()
    patterns = validate_ignore_patterns(ignore)
    out: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not d.endswith(".egg-info")
            and not ignored_path((Path(dirpath) / d).relative_to(root).as_posix(),
                                 patterns, directory=True)
        )
        for name in sorted(filenames):
            if name in SKIP_FILES or name.endswith(SKIP_SUFFIXES) or name.endswith("~"):
                continue
            path = Path(dirpath) / name
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                rel = path.relative_to(root).as_posix()
                if ignored_path(rel, patterns):
                    continue
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            digest = _hash_file(path)
            if digest is None:
                continue
            out[rel] = digest
            if len(out) >= MAX_FILES:
                return out
    return out


def write_tree_snapshot(root: Path, snapshot_path: Path, *, ignore: list[str] | None = None) -> dict:
    """Write the sidecar JSON and return the chained {count, sha256} fields."""
    patterns = validate_ignore_patterns(ignore)
    scope = {"ignore_format": IGNORE_FORMAT, "ignore_patterns": patterns} if patterns else {}
    files = capture_tree(root, ignore=patterns)
    digest = snapshot_digest(files, scope)
    payload = {"files": files, "count": len(files), "sha256": digest, **scope}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    if scope and len(text.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise ValueError("tree snapshot exceeds size bound")
    snapshot_path = snapshot_path.resolve()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        text,
        encoding="utf-8",
    )
    return {"count": len(files), "sha256": digest, **scope}


def snapshot_digest(files: dict[str, str], scope: dict) -> str:
    value = {"files": files, **scope} if scope else files
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def exclusion_scope(meta: dict) -> dict:
    if not any(key in meta for key in ("ignore_format", "ignore_patterns")):
        return {}
    patterns = meta.get("ignore_patterns")
    if (meta.get("ignore_format") != IGNORE_FORMAT or not isinstance(patterns, list)
            or not patterns or validate_ignore_patterns(patterns) != patterns
            or type(meta.get("count")) is not int or not 0 <= meta["count"] <= MAX_FILES
            or not isinstance(meta.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", meta["sha256"]) is None):
        raise ValueError("snapshot exclusion metadata is missing, unsupported or noncanonical")
    return {"ignore_format": IGNORE_FORMAT, "ignore_patterns": patterns}


def scope_from_events(events: list[dict]) -> tuple[dict, dict | None]:
    """New exclusions are bound to every start, including reopened sessions."""
    starts = [row for row in events if row.get("event") == "session.start"]
    if not starts:
        return {}, None
    scoped = [row for row in starts if isinstance(row.get("required_semantics"), (list, str, dict))
              and IGNORE_SEMANTIC in row["required_semantics"]
              or isinstance(row.get("tree_snapshot"), dict)
              and any(key in row["tree_snapshot"] for key in ("ignore_format", "ignore_patterns"))]
    if not scoped:
        return {}, starts[-1].get("tree_snapshot")
    meta = starts[0].get("tree_snapshot")
    if not isinstance(meta, dict) or not exclusion_scope(meta):
        raise ValueError("snapshot exclusions require the original frozen start metadata")
    if any(row.get("tree_snapshot") != meta or
           row.get("required_semantics") != [IGNORE_SEMANTIC] for row in starts):
        raise ValueError("snapshot exclusions changed across starts; use a new session")
    return exclusion_scope(meta), meta


def validate_snapshot(payload: object, meta: dict) -> dict[str, str]:
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, dict):
        raise ValueError("tree snapshot is missing a files object")
    scope = exclusion_scope(meta)
    if scope:
        if exclusion_scope(payload) != scope or len(files) > MAX_FILES:
            raise ValueError("tree snapshot exclusions do not match session.start")
        if (type(meta.get("count")) is not int or type(payload.get("count")) is not int
                or meta["count"] != len(files) or payload["count"] != len(files)):
            raise ValueError("tree snapshot count does not match session.start")
        for path, digest in files.items():
            if (not isinstance(path, str) or not path or "\\" in path or ":" in path
                    or any(part in ("", ".", "..") for part in path.split("/"))
                    or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                    or ignored_path(path, scope["ignore_patterns"])):
                raise ValueError("tree snapshot contains an invalid or excluded file")
    digest = snapshot_digest({str(k): str(v) for k, v in files.items()}, scope)
    if digest != meta.get("sha256") or scope and payload.get("sha256") != digest:
        raise ValueError("tree snapshot digest does not match session.start; the sidecar was changed or replaced")
    return files


def read_snapshot(path: Path, meta: dict) -> dict[str, str]:
    if not path.is_file():
        raise ValueError("undeclared-change snapshot missing")
    scope = exclusion_scope(meta)
    if scope and path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise ValueError("tree snapshot exceeds size bound")
    with path.open("rb") as stream:
        data = stream.read(MAX_SNAPSHOT_BYTES + 1) if scope else stream.read()
    if scope and len(data) > MAX_SNAPSHOT_BYTES:
        raise ValueError("tree snapshot exceeds size bound")
    return validate_snapshot(json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object), meta)


def _unique_object(pairs: list[tuple]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate snapshot JSON key")
        out[key] = value
    return out


def session_exclusions(root: Path, session: str) -> dict:
    """Validate opt-in scope before executing a session's command check."""
    from .ledger import ledger_dir, load_all_events, session_file_stem
    scope, meta = scope_from_events([row for row in load_all_events(root)
                                     if row.get("session") == session])
    if scope:
        read_snapshot(snapshot_file(ledger_dir(root), session_file_stem(session)), meta)
    return scope


def declared_paths(claims: list[dict], root: Path) -> set[str]:
    """Paths named by active (non-retracted) checks."""
    named: set[str] = set()
    root = root.resolve()
    for record in apply_append_retractions(claims):
        if record.get("retracted") and isinstance(record.get("retracts"), dict):
            continue
        if record.get("retracted") or record.get("_append_retraction_reason"):
            continue
        check = record.get("check")
        if not isinstance(check, dict):
            continue
        for key in ("path", "from", "to"):
            rel = _rel_under_root(root, check.get(key))
            if rel:
                named.add(rel)
        artifact = record.get("artifact")
        rel = _rel_under_root(root, artifact)
        if rel:
            named.add(rel)
        argv = check.get("argv")
        if isinstance(argv, list):
            for token in argv:
                rel = _rel_under_root(root, token)
                if rel:
                    named.add(rel)
    return named


def undeclared_results(
    root: Path,
    claims: list[dict],
    start_event: dict | None,
    snapshot_path: Path,
) -> list[dict]:
    """Synthetic RED results for undeclared deletes and content changes."""
    if not isinstance(start_event, dict):
        return []
    meta = start_event.get("tree_snapshot")
    if not isinstance(meta, dict):
        return []
    expected = meta.get("sha256")
    if not isinstance(expected, str) or not expected:
        if any(key in meta for key in ("ignore_format", "ignore_patterns")):
            return [_fail("undeclared-change snapshot invalid", "snapshot exclusion anchor missing")]
        return []

    try:
        files = read_snapshot(snapshot_path, meta)
        scope = exclusion_scope(meta)
    except (OSError, ValueError) as exc:
        return [_fail("undeclared-change snapshot invalid", str(exc))]

    declared = declared_paths(claims, root)
    current = capture_tree(root, ignore=scope.get("ignore_patterns"))
    results: list[dict] = []
    for rel, old_hash in files.items():
        if not isinstance(rel, str) or rel in declared:
            continue
        # A snapshot written before a directory joined SKIP_DIRS still lists
        # its files. Judge the baseline by today's rule, or every such file
        # reads as an undeclared deletion the moment the tool improves.
        if (_in_skipped_dir(rel) or Path(rel).name in SKIP_FILES
                or rel.endswith(SKIP_SUFFIXES) or rel.endswith("~")):
            continue
        if rel not in current:
            results.append(_fail(
                f"undeclared deletion: {rel}",
                f"{rel} existed at session.start and is gone; "
                "no active claim named that path",
            ))
        elif current[rel] != old_hash and not _git_line_endings_only(root / rel, old_hash):
            results.append(_fail(
                f"undeclared change: {rel}",
                f"{rel} changed since session.start; "
                "no active claim named that path",
            ))
    return results


def _git_line_endings_only(path: Path, expected: str) -> bool:
    """Accept LF/CRLF checkout conversion for UTF-8 text, never binary data."""
    try:
        raw = path.read_bytes()
        if b"\x00" in raw:
            return False
        raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    lf = raw.replace(b"\r\n", b"\n")
    return any(hashlib.sha256(candidate).hexdigest() == expected
               for candidate in (lf, lf.replace(b"\n", b"\r\n")))


def unreferenced_artifacts(
    root: Path,
    claims: list[dict],
    artifacts_dir: Path,
) -> list[dict]:
    """Synthetic YELLOW results for artifact files no active claim names.

    Issue: a session can commit a 812-line test log and prove nothing with it.
    `undeclared_results` cannot see these files. It compares the session-start
    snapshot, so a file created during the session never appears, and
    `.showwork` is in SKIP_DIRS anyway. This walks the artifact directory
    directly and names every file no claim points at.
    """
    if not artifacts_dir.is_dir():
        return []
    root = root.resolve()
    declared = declared_paths(claims, root)
    results: list[dict] = []
    for path in sorted(artifacts_dir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except (ValueError, OSError):
            continue
        if rel in declared:
            continue
        results.append(_warn(
            f"unreferenced artifact: {rel}",
            f"{rel} sits in the session artifact directory but no active "
            "claim names it; it ships in the PR and proves nothing",
        ))
        if len(results) >= MAX_UNREFERENCED_ARTIFACTS:
            break
    return results


def merge_undeclared(state: dict, extra: list[dict]) -> dict:
    if not extra:
        return state
    results = list(state.get("results") or []) + extra
    fails = [r for r in results if r["status"] == "fail"]
    errors = [r for r in results if r["status"] == "error"]
    red = [r for r in fails if r.get("severity") == "RED"]
    if red:
        verdict = "RED"
    elif fails or errors:
        verdict = "YELLOW"
    else:
        verdict = "GREEN"
    scored = [r for r in results if not r.get("retracted")]
    passed = sum(1 for r in scored if r["status"] == "pass")
    merged = dict(state)
    merged["results"] = results
    merged["verdict"] = verdict
    merged["total"] = len(scored)
    merged["passed"] = passed
    merged["gaps"] = gaps_payload(merged)
    return merged


def _fail(claim: str, detail: str) -> dict:
    return {
        "claim": claim,
        "session": "",
        "severity": "RED",
        "type": "undeclared_change",
        "status": "fail",
        "detail": detail,
        # Synthetic: the checker made this row, no agent claimed it. It must
        # never satisfy has_minimum_proof, or a session with no claims and one
        # stray file would close clean.
        "synthetic": True,
    }


def escape_result(claim: str, detail: str) -> dict:
    """A RED row for a ledger path that resolves outside the ledger."""
    return _fail(claim, detail)


def _warn(claim: str, detail: str) -> dict:
    """A YELLOW row: merge_undeclared downgrades the verdict but never refuses."""
    return {
        "claim": claim,
        "session": "",
        "severity": "YELLOW",
        "type": "unreferenced_artifact",
        "status": "fail",
        "detail": detail,
        "synthetic": True,
    }


def _files_digest(files: dict[str, str]) -> str:
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_file(path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _in_skipped_dir(rel: str) -> bool:
    """True when any directory segment of a posix-relative path is skipped."""
    parts = rel.split("/")[:-1]
    return any(part in SKIP_DIRS or part.endswith(".egg-info") for part in parts)


def _rel_under_root(root: Path, value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        resolved = (root / value).resolve()
        return resolved.relative_to(root).as_posix()
    except (ValueError, OSError):
        return None
