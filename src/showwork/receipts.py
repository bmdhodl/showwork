"""Read-only receipt overlay for a supervisor UI (BMD desktop).

The UI process never appends. Agents write `.showwork/` in the *user
workspace*. This module maps a live `verify_session` into the four evidence
states BMD already renders: verified, claimed, failed, unknown.

Missing ledgers are unknown, never green. Unreadable JSONL is unknown.
A done with no check-backed claims is claimed, not verified.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from .ledger import (
    claims_for_session,
    has_minimum_proof,
    ledger_dir,
    load_all_events,
    resolve_root,
    session_claims_path,
    session_file_stem,
    sessions_path,
    verify_session,
)
from .audit import audit_root
from .explain import explain_state, redact

READ_ONLY_CHECKS = frozenset({"file_exists", "file_contains", "path_moved", "frontmatter", "glob_count"})

EVIDENCE_STATES = ("verified", "claimed", "failed", "unknown")
LABELS = {
    "verified": "VERIFIED",
    "claimed": "CLAIMED",
    "failed": "FAILED",
    "unknown": "UNKNOWN",
}
SESSION_PREFIX = "bmd-"

# Names this module must never call. The UI is a reader.
_WRITE_APIS = (
    "record_claim",
    "record_event",
    "record_retraction",
    "start_session",
    "finish_session",
)


def sidecar_interpreter() -> str:
    """Interpreter a dispatched agent should use for `python -m showwork`.

    A frozen application executable is not a Python CLI. Frozen callers
    must supply a separately provisioned interpreter explicitly.
    """

    if getattr(sys, "frozen", False):
        raise ValueError("frozen applications must provide a Python interpreter")
    return sys.executable


def session_for_task(task_id: str) -> str:
    """Stable session slug for a BMD dispatch. Reuse if already prefixed."""

    raw = str(task_id or "").strip()
    if not raw:
        raise ValueError("task_id is empty")
    if raw.startswith(SESSION_PREFIX):
        return session_file_stem(raw)
    return session_file_stem(f"{SESSION_PREFIX}{raw}")


def discover_root(
    workspace: str | Path | None,
    agent_cwd: str | Path | None = None,
) -> Path | None:
    """Project root that holds `.showwork/`, or the workspace even if empty."""

    for candidate in (workspace, agent_cwd):
        if candidate is None or str(candidate).strip() == "":
            continue
        path = Path(candidate).expanduser()
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved.is_dir():
            return resolved
    return None


def agent_environ(
    workspace: str | Path,
    task_id: str,
    *,
    interpreter: str | None = None,
) -> dict[str, str]:
    """Env vars for a dispatched Claude/Codex child. Observe mode, not --gate."""

    root = Path(workspace).expanduser().resolve()
    env = {
        "SHOWWORK_SESSION": session_for_task(task_id),
        "SHOWWORK_ROOT": str(root),
        "SHOWWORK_PYTHON": interpreter or sidecar_interpreter(),
    }
    return env


def agent_prompt_block(
    task_id: str,
    *,
    interpreter: str | None = None,
    agent: str = "cursor",
) -> str:
    """Short Outcome Verification block for `build_agent_prompt`. No vault paths."""

    session = session_for_task(task_id)
    python = interpreter or sidecar_interpreter()
    quoted = json.dumps(python)
    agent_name = str(agent or "cursor").strip() or "cursor"
    return (
        "## Outcome Verification (showwork)\n"
        "\n"
        f"This session is `{session}`. The ledger root is `$SHOWWORK_ROOT` "
        "(the workspace you were launched in). Record claims with the sidecar "
        f"interpreter, not a PATH python:\n"
        "\n"
        f"    {quoted} -m showwork start --session {session} --agent {agent_name}\n"
        "\nDeclare acceptance requirements with `showwork require` before completion "
        "claims. Behavior needs an executable command test of the changed path. "
        "File observations use artifact scope and do not certify behavior.\n\n"
        f"    {quoted} -m showwork claim --session {session} "
        "--claim \"<what changed>\" --type file_exists --path <file>\n"
        f"    {quoted} -m showwork finish --session {session} --status ok\n"
        "\n"
        "A clean close needs passing declared acceptance checks. If finish exits 2, "
        "fix the failed behavior. Do not pass --no-verify or use --checks-only "
        "to report an outcome. Commit the complete receipt and run gate. Do not wrap "
        "with --gate: a refused close is a badge, not a dead terminal.\n"
    )


def _session_from_record(record: Mapping[str, Any] | None) -> str | None:
    row = record if isinstance(record, Mapping) else {}
    for key in ("session", "showwork_session"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    task_id = str(row.get("task_id") or "").strip()
    if not task_id:
        return None
    try:
        return session_for_task(task_id)
    except ValueError:
        return None


def _historical_outcome(events: list[dict]) -> str:
    """Last close, separate from the live rerun. A refusal stays a refusal."""
    last = None
    for event in events:
        if event.get("event") in {"session.finish", "session.finish.refused"}:
            last = event
    if not isinstance(last, dict):
        return "absent"
    if last.get("event") == "session.finish.refused":
        return "refused"
    outcome = last.get("outcome")
    if isinstance(outcome, dict) and outcome.get("verdict") in {"VERIFIED", "UNVERIFIED"}:
        return str(outcome["verdict"])
    verdict = last.get("claims_verdict")
    if isinstance(verdict, str) and verdict:
        return verdict
    return "absent"


def _payload(state: str, details: dict[str, Any]) -> dict[str, Any]:
    if state not in EVIDENCE_STATES:
        state = "unknown"
    explanation = details.get("explanation")
    if not isinstance(explanation, dict):
        explanation = explain_state(
            {"verdict": "unknown", "results": [], "outcome": {"verdict": "UNVERIFIED"}},
            integrity=str(details.get("integrity") or "unknown"),
        )
    elif state != "verified" and explanation.get("outcome_verdict") == "VERIFIED":
        explanation = {**explanation, "outcome_verdict": "UNVERIFIED"}
    out = {"state": state, "label": LABELS[state]}
    out.update(details)
    out["explanation"] = explanation
    return out


def _path_unreadable(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return True
    return False


def _has_parse_error(claims: list[dict]) -> bool:
    return any(isinstance(row, dict) and row.get("_parse_error") for row in claims)


def evidence_for_session(root: str | Path | None, session: str) -> dict[str, Any]:
    """Map one session to a BMD evidence badge. Never writes."""

    details: dict[str, Any] = {"session": session, "source": "showwork"}
    if not session or not str(session).strip():
        return _payload("unknown", {**details, "reason": "no session"})
    if root is None or str(root).strip() == "":
        return _payload("unknown", {**details, "reason": "no workspace"})

    try:
        workspace = Path(root).expanduser().resolve()
    except OSError:
        return _payload("unknown", {**details, "reason": "workspace unreadable"})
    details["workspace"] = str(workspace)
    if not workspace.is_dir():
        return _payload("unknown", {**details, "reason": "workspace missing"})

    showwork_dir = ledger_dir(workspace)
    if not showwork_dir.is_dir():
        return _payload(
            "unknown",
            {**details, "reason": "No receipts yet.", "empty": True},
        )

    try:
        if _path_unreadable(sessions_path(workspace, session)) or _path_unreadable(
            session_claims_path(workspace, session)
        ):
            return _payload(
                "unknown",
                {**details, "reason": "ledger unreadable"},
            )
        claims = claims_for_session(workspace, session)
        events = [
            rec for rec in load_all_events(workspace)
            if rec.get("session") == session
        ]
        if _has_parse_error(claims) or _has_parse_error(events):
            return _payload(
                "unknown",
                {**details, "reason": "ledger unreadable"},
            )
        started = any(e.get("event") == "session.start" for e in events)
        if not started and not claims:
            return _payload(
                "unknown",
                {**details, "reason": "No receipts yet.", "empty": True},
            )
        integrity = audit_root(workspace)
        if integrity["verdict"] != "GREEN":
            return _payload("unknown", {
                **details,
                "reason": "ledger integrity is not verified",
                "integrity": integrity["verdict"],
            })
        state = verify_session(workspace, session, allowed_check_types=READ_ONLY_CHECKS)
        historical = _historical_outcome(events)
        details["integrity"] = "GREEN"
        details["explanation"] = explain_state(
            state, integrity="GREEN", historical_outcome=historical,
        )
        open_session = False
        last_status = None
        for event in events:
            if event.get("event") == "session.start":
                open_session = True
            elif event.get("event") == "session.finish":
                open_session = False
                last_status = event.get("status")
        details["verdict"] = state.get("verdict")
        details["passed"] = state.get("passed")
        details["total"] = state.get("total")
        details["claim_count"] = len(claims)
        details["open"] = open_session
        details["last_status"] = last_status
        details["refuse_reason"] = next(
            (
                e.get("refuse_reason")
                for e in reversed(events)
                if e.get("event") == "session.finish.refused" and e.get("refuse_reason")
            ),
            None,
        )
        results = [r for r in state.get("results") or [] if isinstance(r, dict)]
        checked = [r for r in results if r.get("status") != "skipped"]
        failed = [r for r in checked if r.get("status") in {"fail", "error"}
                  and not r.get("policy_disabled")]
        if failed:
            first = failed[0]
            details["claim"] = first.get("claim")
            details["check"] = first.get("type")
            details["detail"] = first.get("detail")
            return _payload("failed", details)
        if any(r.get("policy_disabled") for r in checked):
            return _payload("unknown", {**details, "reason": "checks require active verification"})
        details["outcome"] = state.get("outcome")
        if (has_minimum_proof(state) and state.get("verdict") == "GREEN"
                and state.get("outcome", {}).get("verdict") == "VERIFIED"):
            first = next((r for r in checked if r.get("status") == "pass"), {})
            details["claim"] = first.get("claim")
            details["check"] = first.get("type")
            details["detail"] = first.get("detail")
            return _payload("verified", details)
        prose = next((r for r in results if r.get("status") == "skipped"), {})
        observed = next((r for r in checked if r.get("status") == "pass"), {})
        details["claim"] = prose.get("claim") or observed.get("claim") or "(no check-backed claims)"
        details["check"] = observed.get("type")
        details["detail"] = prose.get("detail") or (
            "individual checks passed; outcome requirements are unverified. " + observed.get("detail", ""))
        return _payload("claimed", details)
    except OSError:
        return _payload("unknown", {**details, "reason": "ledger unreadable"})
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return _payload("unknown", {**details, "reason": "ledger unreadable"})


def overlay_record(
    record: Mapping[str, Any] | None,
    workspace_root: str | Path | None,
    *,
    agent_cwd: str | Path | None = None,
) -> dict[str, Any] | None:
    """Showwork overlay for one BMD run/card. None means no session to join."""

    session = _session_from_record(record)
    if session is None:
        return None
    root = discover_root(workspace_root, agent_cwd)
    return evidence_for_session(root, session)


def decorate_records(
    records: list[dict[str, Any]] | None,
    workspace_root: str | Path | None,
    *,
    agent_cwd: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Attach `verification` without mutating the input list items in place."""

    rows = list(records or [])
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row) if isinstance(row, dict) else {}
        overlay = overlay_record(item, workspace_root, agent_cwd=agent_cwd)
        if overlay is not None:
            item["verification"] = overlay
        out.append(item)
    return out


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_badges_html(
    records: list[dict[str, Any]],
    *,
    title: str = "Receipts",
) -> str:
    """Self-contained Home/Activity badge surface. Click opens the claim."""

    cards = {"home": [], "activity": []}
    if not records:
        records = [{
            "verification": _payload(
                "unknown",
                {"reason": "No receipts yet.", "empty": True, "session": ""},
            ),
            "title": "Empty workspace",
            "surface": "home",
        }]
    for row in records:
        verification = row.get("verification") if isinstance(row.get("verification"), dict) else {}
        state = verification.get("state") if verification.get("state") in EVIDENCE_STATES else "unknown"
        label = LABELS[state]
        heading = _esc(row.get("title") or verification.get("session") or "session")
        surface = row.get("surface") if row.get("surface") in cards else "home"
        claim = _esc(redact(verification.get("claim") or verification.get("reason") or "No receipts yet."))
        check = _esc(redact(verification.get("check") or ""))
        detail = _esc(redact(verification.get("detail") or verification.get("verdict") or ""))
        outcome = verification.get("outcome") or {}
        explanation = verification.get("explanation") if isinstance(verification.get("explanation"), dict) else {}
        scope = _esc(f"Declared checks only: {outcome.get('behavior_checks', 0)} behavior, "
                     f"{outcome.get('artifact_checks', 0)} artifact. Unlisted requirements: unknown.")
        limits = _esc(redact("; ".join(explanation.get("limitations") or [])))
        recovery = _esc(redact(explanation.get("recovery") or ""))
        integrity = _esc(redact(explanation.get("integrity") or verification.get("integrity") or "unknown"))
        session = _esc(verification.get("session") or "")
        row_lines = []
        for item in explanation.get("rows") or []:
            if not isinstance(item, dict):
                continue
            row_lines.append(
                "<p class=\"row\">"
                f"requirement:{_esc(redact(item.get('requirement')))} "
                f"check:{_esc(redact(item.get('check')))} "
                f"scope:{_esc(item.get('scope'))} "
                f"result:{_esc(item.get('result'))} "
                f"evidence:{_esc(item.get('evidence_ref'))} "
                f"revision:{_esc(item.get('revision'))}"
                "</p>"
            )
        rows_html = "".join(row_lines)
        cards[surface].append(
            "<article class=\"card\" data-surface=\""
            f"{surface}\" data-state=\"{state}\">"
            f"<h3>{heading}</h3>"
            f"<details class=\"evidence\" data-state=\"{state}\" data-session=\"{session}\">"
            f"<summary class=\"badge {state}\" data-state=\"{state}\">{label}</summary>"
            "<div class=\"panel\">"
            f"<p class=\"claim\">{claim}</p>"
            f"<p class=\"check\">{check}</p>"
            f"<p class=\"detail\">{detail}</p>"
            f"<p class=\"scope\">{scope}</p>"
            f"<p class=\"integrity\">Integrity: {integrity}</p>"
            f"<p class=\"limits\">{limits}</p>"
            f"<p class=\"recovery\">{recovery}</p>"
            f"{rows_html}"
            "</div></details></article>"
        )
    home = "".join(cards["home"])
    activity = "".join(cards["activity"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>
:root {{ --bg:#0d1117; --fg:#e6edf3; --dim:#8b949e; --line:#30363d; --card:#161b22;
  --verified:#3fb950; --claimed:#d29922; --failed:#f85149; --unknown:#8b949e; }}
body {{ margin:0; padding:1.5rem; background:var(--bg); color:var(--fg);
  font:15px/1.5 ui-sans-serif, sans-serif; }}
h1 {{ font-size:1.2rem; margin:0 0 1rem; }}
h2 {{ font-size:1rem; color:var(--dim); margin:1.5rem 0 .75rem; }}
.grid {{ display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:1rem; }}
.card {{ min-width:0; overflow-wrap:anywhere; }}
.badge {{ display:inline-block; padding:.15rem .55rem; border-radius:999px; font-size:.75rem;
  font-weight:700; letter-spacing:.04em; cursor:pointer; list-style:none; }}
.badge.verified {{ background:color-mix(in srgb,var(--verified) 20%,transparent); color:var(--verified); }}
.badge.claimed {{ background:color-mix(in srgb,var(--claimed) 20%,transparent); color:var(--claimed); }}
.badge.failed {{ background:color-mix(in srgb,var(--failed) 20%,transparent); color:var(--failed); }}
.badge.unknown {{ background:color-mix(in srgb,var(--unknown) 20%,transparent); color:var(--unknown); }}
.panel {{ margin-top:.6rem; color:var(--dim); font-size:.9rem; }}
.claim {{ color:var(--fg); }}
</style>
</head>
<body>
<main class="wrap">
<h1>{_esc(title)}</h1>
<section data-surface="home"><h2>Home</h2><div class="grid">{home}</div></section>
<section data-surface="activity"><h2>Activity</h2><div class="grid">{activity}</div></section>
</main>
</body>
</html>
"""


def receipts_payload(
    workspace: str | Path | None,
    *,
    session: str | None = None,
    task_id: str | None = None,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """JSON payload for `showwork receipts --json`."""

    root = discover_root(workspace)
    rows = list(records or [])
    if not rows:
        if session:
            rows.append({"session": session, "title": session, "surface": "home"})
        elif task_id:
            slug = session_for_task(task_id)
            rows.append({
                "task_id": task_id,
                "session": slug,
                "title": slug,
                "surface": "home",
            })
    decorated = decorate_records(rows, root)
    states = [
        (row.get("verification") or {}).get("state", "unknown")
        for row in decorated
    ]
    return {
        "root": str(root) if root else None,
        "records": decorated,
        "states": states,
        "empty": not root or not (ledger_dir(root).is_dir() if root else False),
    }


def resolve_receipts_root(root: str | Path | None = None) -> Path:
    """Same root rules as the CLI. Exists so tests can pin the lookup."""

    return resolve_root(root)
