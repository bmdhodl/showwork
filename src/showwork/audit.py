"""Integrity audit: prove the ledger is append-only instead of promising it.

Every appended record carries `prev`, the SHA-256 of the previous record
line (or a per-file genesis anchor). Auditing walks each ledger file and
re-derives the chain: modify, delete, or reorder any earlier line and the
first affected record names the exact break.

The last record's hash is the file's *head*. Publishing a head hash
anywhere out-of-band (a commit message, a post, a printout) anchors the
entire history behind it.

Verdicts follow the house algebra:
    GREEN  every chained record verifies; pre-chain records only before the
           chain starts (they are anchored by the first chained record).
    YELLOW a file has records but no chain yet (integrity unprovable), or
           there is nothing to audit.
    RED    a chain break: wrong `prev`, or an unchained record appearing
           after the chain started.
"""

from __future__ import annotations

import json
from pathlib import Path

from .ledger import genesis_hash, ledger_dir, line_hash


def audit_file(path: Path) -> dict:
    """Audit one ledger file's hash chain. Returns a dict with counts, the
    head hash, first break (if any), and a per-file verdict."""
    out: dict = {
        "file": path.name,
        "records": 0,
        "chained": 0,
        "pre_chain": 0,
        "head": None,
        "break_at": None,
        "detail": "",
        "verdict": "GREEN",
    }
    prev_line: str | None = None
    chain_started = False
    line_no = 0
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line_no += 1
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out["records"] += 1
        expected = line_hash(prev_line) if prev_line is not None else genesis_hash(path)
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            rec = None
        prev = rec.get("prev") if isinstance(rec, dict) else None
        if prev is not None:
            chain_started = True
            out["chained"] += 1
            if prev != expected:
                out["verdict"] = "RED"
                out["break_at"] = line_no
                out["detail"] = (f"chain break at line {line_no}: prev is "
                                 f"{prev[:12]}..., expected {expected[:12]}...")
                return out
        else:
            if chain_started:
                out["verdict"] = "RED"
                out["break_at"] = line_no
                out["detail"] = (f"unchained record at line {line_no} after the "
                                 f"chain started: append-only cannot be shown")
                return out
            out["pre_chain"] += 1
        prev_line = line
    if prev_line is not None:
        out["head"] = line_hash(prev_line)
    if out["records"] == 0:
        out["verdict"] = "YELLOW"
        out["detail"] = "empty ledger file: nothing to anchor"
    elif out["chained"] == 0:
        out["verdict"] = "YELLOW"
        out["detail"] = (f"{out['records']} record(s), none chained yet: "
                         f"integrity is unprovable until the first chained append")
    else:
        out["detail"] = (f"intact: {out['chained']} chained record(s)"
                         + (f", {out['pre_chain']} pre-chain record(s) anchored"
                            if out["pre_chain"] else ""))
    return out


def audit_root(root: Path) -> dict:
    """Audit every ledger file under the project root."""
    directory = ledger_dir(root)
    files = sorted(directory.glob("claims-*.jsonl")) if directory.is_dir() else []
    sessions = directory / "sessions.jsonl"
    if sessions.is_file():
        files.append(sessions)
    results = [audit_file(p) for p in files]
    if not results:
        verdict = "YELLOW"
    elif any(r["verdict"] == "RED" for r in results):
        verdict = "RED"
    elif any(r["verdict"] == "YELLOW" for r in results):
        verdict = "YELLOW"
    else:
        verdict = "GREEN"
    return {
        "label": f"audit {directory}",
        "verdict": verdict,
        "files": results,
        "total_records": sum(r["records"] for r in results),
        "total_chained": sum(r["chained"] for r in results),
    }


def render_audit(state: dict) -> str:
    lines = [f"showwork audit  =>  {state['verdict']}  "
             f"({state['total_chained']}/{state['total_records']} records chained)"]
    if not state["files"]:
        lines.append("  no ledger files found")
    for r in state["files"]:
        mark = {"GREEN": "OK ", "YELLOW": "?? ", "RED": "XX "}[r["verdict"]]
        head = f"  head {r['head'][:16]}" if r["head"] else ""
        lines.append(f"  {mark} {r['file']}{head}")
        lines.append(f"       {r['detail']}")
    return "\n".join(lines)
