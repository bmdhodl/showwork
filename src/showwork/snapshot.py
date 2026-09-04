"""Session-start tree snapshot and undeclared-change detection.

Issue #64: verify stayed GREEN when a file no claim named was deleted.
Claims only cover what the agent declared. A start snapshot is prior state
the ledger can compare at verify/finish time.

Old sessions with no tree_snapshot on session.start skip this check.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .checks import apply_append_retractions, gaps_payload

# Generated output is never evidence. A build or a browser run rewrites
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
})
SKIP_FILES = frozenset({
    ".coverage",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
})
SKIP_SUFFIXES = (".pyc", ".pyo", ".swp", ".swo")
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_FILES = 50_000
# One row per dead artifact is a nudge; a thousand is a wall of noise.
MAX_UNREFERENCED_ARTIFACTS = 100


def snapshot_file(ledger: Path, stem: str) -> Path:
    return (ledger / "snapshots" / f"{stem}.json").resolve()


def capture_tree(root: Path) -> dict[str, str]:
    """Map posix-relative paths to SHA-256 hex of file bytes."""
    root = root.resolve()
    out: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not d.endswith(".egg-info")
        )
        for name in sorted(filenames):
            if name in SKIP_FILES or name.endswith(SKIP_SUFFIXES) or name.endswith("~"):
                continue
            path = Path(dirpath) / name
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                rel = path.relative_to(root).as_posix()
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


def write_tree_snapshot(root: Path, snapshot_path: Path) -> dict:
    """Write the sidecar JSON and return the chained {count, sha256} fields."""
    files = capture_tree(root)
    digest = _files_digest(files)
    payload = {"files": files, "count": len(files), "sha256": digest}
    snapshot_path = snapshot_path.resolve()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return {"count": len(files), "sha256": digest}


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
        return []

    path = snapshot_path
    if not path.is_file():
        return [_fail(
            "undeclared-change snapshot missing",
            f"session.start declared tree_snapshot.sha256={expected[:16]} "
            f"but {path.name} is gone",
        )]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_fail(
            "undeclared-change snapshot unreadable",
            f"could not read tree snapshot: {exc}",
        )]
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, dict):
        return [_fail(
            "undeclared-change snapshot invalid",
            "tree snapshot is missing a files object",
        )]
    digest = _files_digest({str(k): str(v) for k, v in files.items()})
    if digest != expected:
        return [_fail(
            "undeclared-change snapshot mismatch",
            "tree snapshot digest does not match session.start; "
            "the sidecar was changed or replaced",
        )]

    declared = declared_paths(claims, root)
    current = capture_tree(root)
    results: list[dict] = []
    for rel, old_hash in files.items():
        if not isinstance(rel, str) or rel in declared:
            continue
        # A snapshot written before a directory joined SKIP_DIRS still lists
        # its files. Judge the baseline by today's rule, or every such file
        # reads as an undeclared deletion the moment the tool improves.
        if _in_skipped_dir(rel):
            continue
        if rel not in current:
            results.append(_fail(
                f"undeclared deletion: {rel}",
                f"{rel} existed at session.start and is gone; "
                "no active claim named that path",
            ))
        elif current[rel] != old_hash:
            results.append(_fail(
                f"undeclared change: {rel}",
                f"{rel} changed since session.start; "
                "no active claim named that path",
            ))
    return results


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
