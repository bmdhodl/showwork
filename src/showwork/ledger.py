"""Append-only claims ledger and session lifecycle.

Layout (under the project root):
    .showwork/
      claims-YYYY-MM-DD.jsonl   one claim record per line, append-only
      sessions.jsonl            session.start / session.finish events

Records are never rewritten. Corrections are append-only retractions that
reference the original claim, so the ledger stays a faithful history of what
was asserted, when, and what was later withdrawn.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from .checks import evaluate_records

LEDGER_DIRNAME = ".showwork"
ROOT_ENV = "SHOWWORK_ROOT"


def resolve_root(root: str | Path | None = None) -> Path:
    if root:
        return Path(root).resolve()
    env = os.environ.get(ROOT_ENV)
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def ledger_dir(root: Path) -> Path:
    return root / LEDGER_DIRNAME


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def claims_path(root: Path, date_str: str | None = None) -> Path:
    return ledger_dir(root) / f"claims-{date_str or _today()}.jsonl"


def sessions_path(root: Path) -> Path:
    return ledger_dir(root) / "sessions.jsonl"


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    """BOM-safe, comment-tolerant JSONL reader. Unparseable lines become
    YELLOW records instead of being silently dropped."""
    if not path.is_file():
        return []
    records: list[dict] = []
    for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            records.append({"claim": f"(unparseable line {i} in {path.name})",
                            "check": None, "_parse_error": str(e),
                            "severity": "YELLOW"})
    return records


# ---------- writing ----------


def record_claim(root: Path, session: str, claim: str, check: dict | None = None,
                 severity: str = "RED", artifact: str | None = None) -> dict:
    rec: dict = {"session": session, "ts": _now(), "claim": claim,
                 "severity": severity.upper()}
    if check:
        rec["check"] = check
    if artifact:
        rec["artifact"] = artifact
    _append(claims_path(root), rec)
    return rec


def record_retraction(root: Path, session: str, claim: str, reason: str) -> dict:
    rec = {"session": session, "ts": _now(), "retracted": True,
           "retracts": {"session": session, "claim": claim},
           "retraction_reason": reason}
    _append(claims_path(root), rec)
    return rec


def record_event(root: Path, event: str, session: str, **fields) -> dict:
    rec = {"event": event, "session": session, "ts": _now()}
    rec.update({k: v for k, v in fields.items() if v is not None})
    _append(sessions_path(root), rec)
    return rec


# ---------- reading ----------


def load_claims(root: Path, date_str: str | None = None) -> list[dict]:
    return _read_jsonl(claims_path(root, date_str))


def load_all_claims(root: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(ledger_dir(root).glob("claims-*.jsonl")):
        records.extend(_read_jsonl(path))
    return records


def claims_for_session(root: Path, session: str) -> list[dict]:
    out = []
    for r in load_all_claims(root):
        if r.get("session") == session:
            out.append(r)
        elif isinstance(r.get("retracts"), dict) and r["retracts"].get("session") == session:
            out.append(r)
    return out


# ---------- verification entry points ----------


def verify_date(root: str | Path | None = None, date_str: str | None = None) -> dict:
    rt = resolve_root(root)
    label = date_str or _today()
    return evaluate_records(load_claims(rt, label), rt, label=label)


def verify_session(root: str | Path | None = None, session: str = "") -> dict:
    rt = resolve_root(root)
    return evaluate_records(claims_for_session(rt, session), rt,
                            label=f"session {session}")


# ---------- session lifecycle ----------


def start_session(root: Path, session: str, agent: str | None = None,
                  note: str | None = None) -> dict:
    return record_event(root, "session.start", session, agent=agent, note=note)


def finish_session(root: Path, session: str, status: str = "ok",
                   no_verify: bool = False, note: str | None = None) -> tuple[int, dict | None]:
    """Close a session. A clean close (`status=ok`) verifies this session's own
    claims first and REFUSES (exit 2) if any is RED: a green exit with a red
    ledger is not done. `status=blocked` or `no_verify=True` closes without
    gating, and the bypass is stamped on the event as a durable residual."""
    state = None
    verdict = None
    if status == "ok" and not no_verify:
        state = verify_session(root, session)
        verdict = state["verdict"]
        if verdict == "RED":
            record_event(root, "session.finish.refused", session,
                         status=status, claims_verdict=verdict, note=note)
            return 2, state
    record_event(root, "session.finish", session, status=status,
                 claims_verdict=verdict,
                 verify_bypassed=(True if (no_verify and status == "ok") else None),
                 note=note)
    return 0, state
