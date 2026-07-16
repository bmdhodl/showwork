"""False Done Rate (FDR): how often agents claim work that is not backed by
reality - measured ONLY from durable ledger evidence.

    python scripts/false_done_rate.py [--json] [--label NAME=PATH ...] [ROOT ...]

Definition (pre-registered in docs/false-done-rate.md - read it before
quoting numbers):

  eligible session   a session that recorded >= 1 claim carrying a check and
                     attempted at least one close (finish or refused-finish).
  false-done event   durable evidence that a "done" was not real when it was
                     asserted:
                       - a `session.finish.refused` event (the exit gate
                         REFUSED a clean close), or
                       - an append-only retraction record, or
                       - a close stamped `claims_verdict: RED` (blocked /
                         bypassed / stop-hook observed), or
                       - a close stamped `verify_bypassed` (unverifiable by
                         choice: counted separately AND as false-done-risk).
  FDR (session)      sessions with >= 1 false-done event / eligible sessions.
  FDR (event)        false-done events / (false-done events + clean closes).

This measures a LOWER BOUND: an agent that quietly fixes reality before its
first `finish` leaves no durable evidence and is invisible here. That is the
honest direction to be wrong in.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def analyze_root(root: Path) -> dict:
    ledger = root / ".showwork"
    sessions_events = _read_jsonl(ledger / "sessions.jsonl")
    claims: list[dict] = []
    for p in sorted(ledger.glob("claims-*.jsonl")):
        claims.extend(_read_jsonl(p))

    checked_claims = [c for c in claims if isinstance(c.get("check"), dict)]
    retractions = [c for c in claims
                   if c.get("retracted") and isinstance(c.get("retracts"), dict)]

    per: dict[str, dict] = {}

    def s(name: str) -> dict:
        return per.setdefault(name, {
            "agent": None, "checked_claims": 0, "retractions": 0,
            "refused": 0, "red_closes": 0, "bypassed": 0, "clean_closes": 0,
            "closes": 0,
        })

    for c in checked_claims:
        s(str(c.get("session", "?")))["checked_claims"] += 1
    for r in retractions:
        s(str(r["retracts"].get("session", "?")))["retractions"] += 1
    for e in sessions_events:
        name = str(e.get("session", "?"))
        ev = e.get("event")
        if ev == "session.start" and e.get("agent"):
            s(name)["agent"] = e["agent"]
        elif ev == "session.finish.refused":
            s(name)["refused"] += 1
        elif ev == "session.finish":
            rec = s(name)
            rec["closes"] += 1
            if e.get("verify_bypassed"):
                rec["bypassed"] += 1
            elif e.get("claims_verdict") == "RED":
                rec["red_closes"] += 1
            else:
                rec["clean_closes"] += 1

    eligible = {k: v for k, v in per.items()
                if v["checked_claims"] > 0 and (v["closes"] + v["refused"]) > 0}
    false_done = {k: v for k, v in eligible.items()
                  if v["refused"] or v["retractions"] or v["red_closes"] or v["bypassed"]}

    events_false = sum(v["refused"] + v["retractions"] + v["red_closes"] + v["bypassed"]
                       for v in eligible.values())
    events_clean = sum(v["clean_closes"] for v in eligible.values())

    return {
        "root": str(root),
        "eligible_sessions": len(eligible),
        "false_done_sessions": len(false_done),
        "fdr_session": (len(false_done) / len(eligible)) if eligible else None,
        "false_done_events": events_false,
        "clean_closes": events_clean,
        "fdr_event": (events_false / (events_false + events_clean))
                     if (events_false + events_clean) else None,
        "checked_claims": sum(v["checked_claims"] for v in eligible.values()),
        "sessions": {k: eligible[k] for k in sorted(eligible)},
        "false_done_session_ids": sorted(false_done),
    }


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render(reports: list[tuple[str, dict]]) -> str:
    lines = ["# False Done Rate", "",
             "Durable-evidence lower bound; methodology: docs/false-done-rate.md", "",
             "| corpus | eligible sessions | false-done sessions | FDR (session) | FDR (event) | checked claims |",
             "|---|---:|---:|---:|---:|---:|"]
    te = tf = 0
    ee = ef = 0
    for label, r in reports:
        lines.append(f"| {label} | {r['eligible_sessions']} | {r['false_done_sessions']} "
                     f"| {_pct(r['fdr_session'])} | {_pct(r['fdr_event'])} "
                     f"| {r['checked_claims']} |")
        te += r["eligible_sessions"]; tf += r["false_done_sessions"]
        ee += r["false_done_events"]; ef += r["clean_closes"]
    lines.append(f"| **all** | **{te}** | **{tf}** "
                 f"| **{_pct(tf / te if te else None)}** "
                 f"| **{_pct(ee / (ee + ef) if (ee + ef) else None)}** |  |")
    lines.append("")
    for label, r in reports:
        if r["false_done_session_ids"]:
            lines.append(f"False-done sessions in {label}: "
                         + ", ".join(f"`{s}`" for s in r["false_done_session_ids"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="False Done Rate from showwork ledgers")
    ap.add_argument("roots", nargs="*", default=["."],
                    help="project roots containing .showwork/")
    ap.add_argument("--label", action="append", default=[],
                    help="NAME=PATH labeled corpus (repeatable)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    corpora: list[tuple[str, Path]] = []
    for item in args.label:
        name, _, path = item.partition("=")
        corpora.append((name, Path(path)))
    for r in (args.roots if not corpora or args.roots != ["."] else []):
        corpora.append((Path(r).name or str(r), Path(r)))
    if not corpora:
        corpora = [(".", Path("."))]

    reports = [(label, analyze_root(root)) for label, root in corpora]
    if args.json:
        print(json.dumps({label: r for label, r in reports}, indent=2))
    else:
        print(render(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
