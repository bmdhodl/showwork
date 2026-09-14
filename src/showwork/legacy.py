"""Opt-in, immutable acknowledgement of damaged legacy shared ledgers.

This does not repair or approve old records. Every pinned legacy file stays
present and byte-identical (apart from Git's LF/CRLF checkout conversion).
Current per-session receipts are never eligible for this acknowledgement.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess
import tempfile


def inspect_legacy_baseline(root: Path, session: str, commit: str) -> dict:
    from .audit import audit_file
    from .ledger import _read_jsonl, session_file_stem

    result = {"commit": commit, "frozen_files": 0, "acknowledged": [], "errors": []}

    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, timeout=15)

    def refuse(message):
        result["errors"].append(message)
        return result

    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        return refuse("legacy integrity baseline requires a full immutable Git commit ID")
    kind = git("cat-file", "-t", commit)
    if kind.returncode or kind.stdout.strip() != b"commit":
        return refuse("legacy integrity baseline commit does not exist")
    if git("merge-base", "--is-ancestor", commit, "HEAD").returncode:
        return refuse("legacy integrity baseline must be an ancestor of HEAD")
    stem = session_file_stem(session)
    if git("cat-file", "-e", f"{commit}:.showwork/sessions/{stem}.jsonl").returncode == 0:
        return refuse("legacy integrity baseline must predate the selected session")

    listing = git("ls-tree", "-r", "--name-only", commit, "--", ".showwork/")
    if listing.returncode:
        return refuse("cannot read legacy integrity baseline tree")
    paths = [rel for rel in listing.stdout.decode("utf-8").splitlines()
             if re.fullmatch(r"\.showwork/(sessions|claims-\d{4}-\d{2}-\d{2})\.jsonl", rel)]
    if not paths:
        return refuse("legacy integrity baseline contains no shared legacy ledgers")
    with tempfile.TemporaryDirectory(prefix="showwork-legacy-") as directory:
        for rel in paths:
            blob = git("show", f"{commit}:{rel}")
            path = root / rel
            if (blob.returncode or not path.is_file() or path.is_symlink()
                    or not path.resolve().is_relative_to(root)
                    or path.read_bytes().replace(b"\r\n", b"\n") != blob.stdout.replace(b"\r\n", b"\n")):
                result["errors"].append(f"legacy baseline file changed, moved or missing: {rel}")
                continue
            result["frozen_files"] += 1
            if any(row.get("session") == session for row in _read_jsonl(path)):
                result["errors"].append(f"legacy baseline cannot acknowledge the selected session: {rel}")
                continue
            # Genesis hashes use the basename, so an isolated copy produces
            # the same audit without modifying the project's original files.
            saved = Path(directory) / path.name
            saved.write_bytes(blob.stdout)
            audit = audit_file(saved)
            if audit["verdict"] == "RED":
                result["acknowledged"].append({
                    "path": rel, "verdict": "RED", "detail": audit["detail"],
                    "sha256_lf": hashlib.sha256(blob.stdout.replace(b"\r\n", b"\n")).hexdigest(),
                })
    return result
