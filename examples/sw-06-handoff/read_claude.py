"""Read one handoff from receipt files and the local decision.

This process runs `receipts` only. It does not run verify or gate, and it
does not execute the recorded command. A model summary is not an input.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
NO_MERGE = "This text does not authorize a merge or a clean close."


def child_env() -> dict[str, str]:
    env = os.environ.copy()
    src = REPO / "src"
    if (src / "showwork" / "__init__.py").is_file():
        prev = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(src) + (os.pathsep + prev if prev else "")
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    env.pop("SHOWWORK_COMMAND_TIMEOUT_SECONDS", None)
    return env


def load_decision(root: Path) -> dict | None:
    path = root / "decision.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def source_name(root: Path, decision: dict | None) -> str:
    if not isinstance(decision, dict):
        return "absent"
    source = decision.get("source")
    if not isinstance(source, str) or source == "":
        return "absent"
    parts = Path(source).parts
    if Path(source).is_absolute() or ".." in parts:
        return "absent"
    if not (root / source).is_file():
        return "absent"
    return source


def finish_event(root: Path, session: str) -> dict | None:
    path = root / ".showwork" / "sessions" / f"{session}.jsonl"
    if not path.is_file():
        return None
    last = None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None
        if row.get("event") == "session.finish" and row.get("session") == session:
            last = row
    return last


def command_evidence(finish: dict | None) -> dict | None:
    if not isinstance(finish, dict):
        return None
    items = finish.get("command_evidence")
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence")
        if item.get("requirement_id") == "run" and isinstance(evidence, dict):
            return evidence
    return None


def receipts(root: Path, session: str) -> dict:
    proc = subprocess.run(
        [
            sys.executable, "-m", "showwork.cli", "--root", str(root),
            "receipts", "--session", session, "--json",
        ],
        cwd=root, env=child_env(), text=True, capture_output=True, check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not records:
        return {}
    verification = records[0].get("verification")
    return verification if isinstance(verification, dict) else {}


def script_is_stale(root: Path, evidence: dict | None) -> bool:
    if not isinstance(evidence, dict):
        return False
    recorded = evidence.get("script_sha256")
    if not isinstance(recorded, str) or recorded == "":
        return False
    script = root / "check.py"
    if not script.is_file():
        return True
    current = hashlib.sha256(script.read_bytes()).hexdigest()
    return current != recorded


def revision_of(evidence: dict | None) -> str:
    if not isinstance(evidence, dict):
        return "absent"
    commit = evidence.get("git_commit")
    if isinstance(commit, str) and re.fullmatch(r"[0-9a-fA-F]{7,64}", commit):
        return commit[:12]
    return "absent"


def limit_of(evidence: dict | None) -> int | None:
    if not isinstance(evidence, dict):
        return None
    value = evidence.get("timeout_seconds")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def read_handoff(root: Path, session: str) -> dict:
    decision = load_decision(root)
    source = source_name(root, decision)
    governs = isinstance(decision, dict) and decision.get("session") == session
    superseded = (
        isinstance(decision, dict)
        and isinstance(decision.get("superseded_by"), str)
        and decision.get("superseded_by") != ""
    )
    finish = finish_event(root, session)
    evidence = command_evidence(finish)
    badge = receipts(root, session)
    explanation = badge.get("explanation") if isinstance(badge.get("explanation"), dict) else {}
    rows = explanation.get("rows") if isinstance(explanation.get("rows"), list) else []
    requirements = []
    failed_check = None
    command_disabled = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("result") == "fail" and failed_check is None:
            failed_check = row.get("check") or "absent"
        if row.get("check") == "command" and row.get("result") == "disabled":
            command_disabled = True
        requirement_id = row.get("requirement_id")
        if isinstance(requirement_id, str) and requirement_id:
            requirements.append({
                "id": requirement_id,
                "text": row.get("requirement") or "absent",
                "check": row.get("check") or "absent",
                "result": row.get("result") or "unknown",
            })
    receipt_state = badge.get("state") if isinstance(badge.get("state"), str) else "unknown"
    code_stale = script_is_stale(root, evidence)
    if not governs or finish is None:
        view = "unknown"
    elif superseded or code_stale:
        view = "stale"
    elif failed_check is not None:
        view = "failed"
    elif receipt_state == "unknown" and not command_disabled:
        view = "unknown"
    else:
        view = "current"
    if view == "unknown":
        next_step = (
            "Evidence is missing or the session does not match. "
            "Do not reuse another session. " + NO_MERGE
        )
    elif superseded:
        next_step = (
            "The governing decision is superseded. "
            "Do not reuse the old approval. " + NO_MERGE
        )
    elif code_stale:
        next_step = (
            "The checked file changed after the receipt. "
            "Run gate before you trust the old command result. " + NO_MERGE
        )
    elif failed_check is not None:
        next_step = (
            "Repair the failed check, then rerun verify. " + NO_MERGE
        )
    elif command_disabled:
        limit = limit_of(evidence)
        limit_text = f"{limit} seconds" if limit is not None else "absent"
        next_step = (
            "The command check did not run on this read. "
            f"Its limit is {limit_text}. "
            "Run gate to execute it. " + NO_MERGE
        )
    else:
        next_step = (
            "The file check passed on this read. " + NO_MERGE
        )
    return {
        "session": session,
        "requirements": requirements,
        "governing_id": decision.get("id") if governs and isinstance(decision, dict) else "absent",
        "governing_source": source if governs else "absent",
        "revision": revision_of(evidence) if governs else "absent",
        "limit_seconds": limit_of(evidence) if governs else None,
        "failed_check": failed_check,
        "receipt_state": receipt_state,
        "view": view,
        # A read never inherits a close. The next step names the repair.
        "approval": False,
        "next_step": next_step,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3 or args[1] != "--session" or args[2] == "":
        print("usage: read_claude.py <directory> --session <id>", file=sys.stderr)
        return 2
    card = read_handoff(Path(args[0]).resolve(), args[2])
    print(json.dumps(card, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
