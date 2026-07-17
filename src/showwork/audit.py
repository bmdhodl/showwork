"""Integrity audit: prove the ledger is append-only instead of promising it.

Every appended record carries `prev`, the SHA-256 of a previous record line
(or a per-file genesis anchor). Auditing walks each ledger file and re-derives
the chain: modify, delete, or reorder any anchored line and the first affected
record names the exact break.

Concurrent sessions that append and later merge produce a *fork*: two record
blocks whose `prev` points at the same earlier line. A fork is not tampering,
so a record whose `prev` matches *any earlier line* (not only its immediate
predecessor) is accepted and counted as a fork, while a `prev` that matches no
earlier line stays RED at the exact line. See docs/concurrency.md.

A file's *heads* are its tip lines — the ones nothing else chains off. A linear
file has one head; a forked file has one per branch. Publishing a head hash
out-of-band (a commit message, a post, a printout) anchors that branch behind
it. `head` (singular) is the last record line, kept for compatibility.

Verdicts follow the house algebra:
    GREEN  every chained record anchors to an earlier line (or genesis);
           pre-chain records only before the chain starts. Forks are GREEN
           and reported, not hidden (use --strict to forbid them).
    YELLOW a file has records but no chain yet (integrity unprovable), or
           there is nothing to audit.
    RED    a chain break: a `prev` matching no earlier line, an unchained
           record after the chain started, or a fork under --strict.
"""

from __future__ import annotations

import json
from pathlib import Path

from .ledger import genesis_hash, ledger_dir, line_hash


def audit_file(path: Path, strict: bool = False) -> dict:
    """Audit one ledger file's hash chain. Returns a dict with counts, the
    head hash, the branch heads, the fork count, first break (if any), and a
    per-file verdict. With ``strict=True`` a fork is a RED break rather than an
    accepted concurrent branch."""
    out: dict = {
        "file": path.name,
        "records": 0,
        "chained": 0,
        "pre_chain": 0,
        "forks": 0,
        "head": None,
        "heads": [],
        "break_at": None,
        "detail": "",
        "verdict": "GREEN",
    }
    genesis = genesis_hash(path)
    # Every hash an anchor may legitimately point back at: the genesis anchor,
    # plus each record line already seen. A `prev` in this set is either the
    # immediate predecessor (a linear step) or an earlier line (a fork). A
    # `prev` outside it is tampering — the anchored bytes changed or vanished.
    seen: set[str] = {genesis}
    referenced: set[str] = set()  # hashes used as some record's prev
    record_hashes: list[str] = []  # hash of every record line, in file order
    prev_line: str | None = None
    chain_started = False
    line_no = 0
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as e:
        out["verdict"] = "RED"
        out["detail"] = f"ledger file is not valid UTF-8: {e}"
        return out
    except FileNotFoundError:
        out["verdict"] = "YELLOW"
        out["detail"] = "ledger file missing: nothing to anchor"
        return out
    for raw in text.splitlines():
        line_no += 1
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out["records"] += 1
        expected = line_hash(prev_line) if prev_line is not None else genesis
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            rec = None
        prev = rec.get("prev") if isinstance(rec, dict) else None
        if prev is not None:
            chain_started = True
            out["chained"] += 1
            if prev == expected:
                pass  # linear step: anchors to the immediate predecessor
            elif isinstance(prev, str) and prev in seen:
                # Anchors to an earlier line (or a second genesis root): a fork,
                # not a break. This is what a legitimate concurrent merge looks
                # like once git has union-concatenated the two branches.
                out["forks"] += 1
                if strict:
                    out["verdict"] = "RED"
                    out["break_at"] = line_no
                    out["detail"] = (f"fork at line {line_no}: prev "
                                     f"{prev[:12]}... re-anchors to an earlier "
                                     f"line; --strict forbids concurrent branches")
                    return out
            else:
                out["verdict"] = "RED"
                out["break_at"] = line_no
                out["detail"] = (f"chain break at line {line_no}: prev is "
                                 f"{str(prev)[:12]}..., matches no earlier line "
                                 f"(expected {expected[:12]}...)")
                return out
            referenced.add(prev)
        else:
            if chain_started:
                out["verdict"] = "RED"
                out["break_at"] = line_no
                out["detail"] = (f"unchained record at line {line_no} after the "
                                 f"chain started: append-only cannot be shown")
                return out
            out["pre_chain"] += 1
        h = line_hash(line)
        seen.add(h)
        record_hashes.append(h)
        prev_line = line
    if prev_line is not None:
        out["head"] = record_hashes[-1]
    # Heads are tip lines: record-line hashes nothing else anchored to. One per
    # branch. Only meaningful once a chain exists; a pre-chain-only file has no
    # provable tips to publish.
    if out["chained"]:
        out["heads"] = [h for h in record_hashes if h not in referenced]
    if out["records"] == 0:
        out["verdict"] = "YELLOW"
        out["detail"] = "empty ledger file: nothing to anchor"
    elif out["chained"] == 0:
        out["verdict"] = "YELLOW"
        out["detail"] = (f"{out['records']} record(s), none chained yet: "
                         f"integrity is unprovable until the first chained append")
    else:
        detail = f"intact: {out['chained']} chained record(s)"
        if out["pre_chain"]:
            detail += f", {out['pre_chain']} pre-chain record(s) anchored"
        if out["forks"]:
            detail += (f"; {out['forks']} fork(s) across {len(out['heads'])} "
                       f"branch head(s); publish heads to anchor the tips")
        out["detail"] = detail
    return out


def audit_root(root: Path, strict: bool = False) -> dict:
    """Audit every ledger file under the project root."""
    directory = ledger_dir(root)
    files = sorted(directory.glob("claims-*.jsonl")) if directory.is_dir() else []
    sessions = directory / "sessions.jsonl"
    if sessions.is_file():
        files.append(sessions)
    results = [audit_file(p, strict=strict) for p in files]
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
        "total_forks": sum(r["forks"] for r in results),
    }


def render_audit(state: dict) -> str:
    forks = state.get("total_forks", 0)
    fork_note = f", {forks} fork(s)" if forks else ""
    lines = [f"showwork audit  =>  {state['verdict']}  "
             f"({state['total_chained']}/{state['total_records']} records chained"
             f"{fork_note})"]
    if not state["files"]:
        lines.append("  no ledger files found")
    for r in state["files"]:
        mark = {"GREEN": "OK ", "YELLOW": "?? ", "RED": "XX "}[r["verdict"]]
        head = f"  head {r['head'][:16]}" if r["head"] else ""
        forked = f"  ({r['forks']} fork, {len(r['heads'])} heads)" if r.get("forks") else ""
        lines.append(f"  {mark} {r['file']}{head}{forked}")
        lines.append(f"       {r['detail']}")
    return "\n".join(lines)
