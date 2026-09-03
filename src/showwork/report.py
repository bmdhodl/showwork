"""Operator reports: session status, usage mix, and False Done Rate.

FDR methodology is pre-registered in docs/false-done-rate.md. This module
exposes the same durable-evidence rates for `showwork report` without leaving
the package.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from .checks import evaluate_records
from .ledger import claims_for_session, load_all_claims, load_all_events


def _parse_since(since: str | None) -> datetime | None:
    if since is None or since == "":
        return None
    text = since.strip()
    try:
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return datetime.fromisoformat(text)
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise ValueError(f"invalid --since date {since!r}; use YYYY-MM-DD") from exc


def _ts_ok(ts: object, since: datetime | None) -> bool:
    if since is None:
        return True
    if not isinstance(ts, str) or ts == "":
        return False
    try:
        # Ledger stamps are usually "YYYY-MM-DDTHH:MM:SSZ" or with offset.
        cleaned = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt >= since
    except ValueError:
        return False


def _is_campaign_session(session: str, note: str | None = None) -> bool:
    """Proof-burst sessions from sources/research_* campaigns.

    Convention (not a ledger rewrite): session id or start note contains a
    campaign marker such as proof, research_, evidence, dashboard.
    """
    blob = f"{session} {note or ''}".lower()
    return any(
        m in blob
        for m in (
            "proof", "research_", "evidence", "dashboard",
            "sanitize-replay", "fixture-r",
        )
    )


def analyze_fdr(root: Path, *, since: str | None = None,
                exclude_campaign: bool = False) -> dict:
    """False Done Rate for one project root (same definitions as the script)."""
    since_dt = _parse_since(since)
    sessions_events = [
        e for e in load_all_events(root)
        if _ts_ok(e.get("ts"), since_dt)
    ]
    claims = [
        rec for rec in load_all_claims(root)
        if _ts_ok(rec.get("ts"), since_dt)
    ]

    checked_claims = [c for c in claims if isinstance(c.get("check"), dict)]
    retractions = [c for c in claims
                   if c.get("retracted") and isinstance(c.get("retracts"), dict)]

    start_notes: dict[str, str | None] = {}
    per: dict[str, dict] = {}

    def s(name: str) -> dict:
        return per.setdefault(name, {
            "agent": None, "checked_claims": 0, "retractions": 0,
            "refused": 0, "red_closes": 0, "bypassed": 0, "clean_closes": 0,
            "closes": 0, "campaign": False,
        })

    for e in sessions_events:
        if e.get("event") == "session.start":
            name = str(e.get("session", "?"))
            start_notes[name] = e.get("note")
            if e.get("agent"):
                s(name)["agent"] = e["agent"]

    for c in checked_claims:
        name = str(c.get("session", "?"))
        s(name)["checked_claims"] += 1
    for r in retractions:
        s(str(r["retracts"].get("session", "?")))["retractions"] += 1
    for e in sessions_events:
        name = str(e.get("session", "?"))
        ev = e.get("event")
        if ev == "session.finish.refused":
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

    for name, rec in per.items():
        rec["campaign"] = _is_campaign_session(name, start_notes.get(name))

    eligible = {k: v for k, v in per.items()
                if v["checked_claims"] > 0 and (v["closes"] + v["refused"]) > 0}
    if exclude_campaign:
        eligible = {k: v for k, v in eligible.items() if not v["campaign"]}

    false_done = {k: v for k, v in eligible.items()
                  if v["refused"] or v["retractions"] or v["red_closes"] or v["bypassed"]}

    events_false = sum(v["refused"] + v["retractions"] + v["red_closes"] + v["bypassed"]
                       for v in eligible.values())
    events_clean = sum(v["clean_closes"] for v in eligible.values())

    return {
        "root": str(root),
        "since": since,
        "exclude_campaign": exclude_campaign,
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


def usage_report(root: Path, *, since: str | None = None,
                 exclude_campaign: bool = False) -> dict:
    """Sessions, agents, check-type mix, FDR window for one root."""
    since_dt = _parse_since(since)
    fdr = analyze_fdr(root, since=since, exclude_campaign=exclude_campaign)

    starts = 0
    finishes = 0
    refused = 0
    agents: dict[str, int] = {}
    check_types: dict[str, int] = {}
    campaign_starts = 0

    start_notes: dict[str, str | None] = {}
    for e in load_all_events(root):
        if not _ts_ok(e.get("ts"), since_dt):
            continue
        ev = e.get("event")
        session = str(e.get("session", "?"))
        if ev == "session.start":
            starts += 1
            start_notes[session] = e.get("note")
            if _is_campaign_session(session, e.get("note")):
                campaign_starts += 1
            agent = e.get("agent") or "(none)"
            agents[str(agent)] = agents.get(str(agent), 0) + 1
        elif ev == "session.finish":
            finishes += 1
        elif ev == "session.finish.refused":
            refused += 1

    for c in load_all_claims(root):
        if not _ts_ok(c.get("ts"), since_dt):
            continue
        check = c.get("check")
        if not isinstance(check, dict):
            continue
        session = str(c.get("session", ""))
        if exclude_campaign and _is_campaign_session(session, start_notes.get(session)):
            continue
        ctype = str(check.get("type") or "?")
        check_types[ctype] = check_types.get(ctype, 0) + 1

    return {
        "root": str(root),
        "since": since,
        "exclude_campaign": exclude_campaign,
        "session_starts": starts,
        "session_finishes": finishes,
        "session_refused": refused,
        "campaign_starts": campaign_starts,
        "agents": dict(sorted(agents.items(), key=lambda kv: (-kv[1], kv[0]))),
        "check_types": dict(sorted(check_types.items(), key=lambda kv: (-kv[1], kv[0]))),
        "fdr": {
            "eligible_sessions": fdr["eligible_sessions"],
            "false_done_sessions": fdr["false_done_sessions"],
            "fdr_session": fdr["fdr_session"],
            "fdr_event": fdr["fdr_event"],
            "checked_claims": fdr["checked_claims"],
            "false_done_session_ids": fdr["false_done_session_ids"],
        },
        "as_of": date.today().isoformat(),
    }


def session_status(root: Path, session: str | None = None) -> dict:
    """Open vs closed, last verdict, and unverified gaps."""
    events = load_all_events(root)
    by_session: dict[str, list[dict]] = {}
    for e in events:
        name = str(e.get("session", "?"))
        by_session.setdefault(name, []).append(e)

    names = [session] if session else sorted(by_session)
    rows = []
    for name in names:
        evs = by_session.get(name, [])
        started = any(e.get("event") == "session.start" for e in evs)
        finishes = [e for e in evs if e.get("event") == "session.finish"]
        refused = [e for e in evs if e.get("event") == "session.finish.refused"]
        last_close = None
        for e in evs:
            if e.get("event") in ("session.finish", "session.finish.refused"):
                last_close = e
        open_ = False
        for e in evs:
            if e.get("event") == "session.start":
                open_ = True
            elif e.get("event") == "session.finish":
                open_ = False
        # Prefer live verify for open sessions; else last stamped verdict.
        state = evaluate_records(claims_for_session(root, name), root,
                                 label=f"session {name}")
        rows.append({
            "session": name,
            "started": started,
            "open": open_,
            "finish_count": len(finishes),
            "refuse_count": len(refused),
            "last_status": (last_close or {}).get("status"),
            "last_claims_verdict": (last_close or {}).get("claims_verdict"),
            "live_verdict": state["verdict"],
            "live_passed": state["passed"],
            "live_total": state["total"],
            "gaps": state["gaps"],
            "agent": next((e.get("agent") for e in evs
                           if e.get("event") == "session.start" and e.get("agent")), None),
        })
    return {"root": str(root), "sessions": rows}


def render_usage(report: dict) -> str:
    fdr = report["fdr"]
    lines = [
        f"# showwork report — {report['root']}",
        f"as_of {report['as_of']}"
        + (f"; since {report['since']}" if report.get("since") else "")
        + ("; exclude_campaign" if report.get("exclude_campaign") else ""),
        "",
        f"starts={report['session_starts']} finishes={report['session_finishes']} "
        f"refused={report['session_refused']} campaign_starts={report['campaign_starts']}",
        "",
        "## Agents",
    ]
    for agent, n in report["agents"].items():
        lines.append(f"- {agent}: {n}")
    lines.append("")
    lines.append("## Check types")
    for ctype, n in report["check_types"].items():
        lines.append(f"- {ctype}: {n}")
    lines += [
        "",
        "## False Done Rate",
        f"eligible={fdr['eligible_sessions']} false_done={fdr['false_done_sessions']} "
        f"FDR_session={_pct(fdr['fdr_session'])} FDR_event={_pct(fdr['fdr_event'])} "
        f"checked_claims={fdr['checked_claims']}",
        "",
        "methodology: docs/false-done-rate.md",
    ]
    return "\n".join(lines)


def render_status(status: dict) -> str:
    lines = [f"# showwork status — {status['root']}", ""]
    for row in status["sessions"]:
        state = "OPEN" if row["open"] else ("closed" if row["started"] else "no-start")
        lines.append(
            f"- {row['session']}: {state} live={row['live_verdict']} "
            f"({row['live_passed']}/{row['live_total']})"
            + (f" agent={row['agent']}" if row.get("agent") else "")
        )
        if row["gaps"]:
            for g in row["gaps"][:5]:
                lines.append(f"    gap: {g['claim']} — {g['detail']}")
    if not status["sessions"]:
        lines.append("(no sessions)")
    return "\n".join(lines)


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"
