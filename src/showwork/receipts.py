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
    sessions_path,
    verify_session,
)
from .report import session_status

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

    Frozen PyInstaller sets `sys.executable` to the sidecar binary. That is
    still the right process: `-m showwork` loads the bundled package. Do not
    search PATH for another `python`.
    """

    return sys.executable


def session_for_task(task_id: str) -> str:
    """Stable session slug for a BMD dispatch. Reuse if already prefixed."""

    raw = str(task_id or "").strip()
    if not raw:
        raise ValueError("task_id is empty")
    if raw.startswith(SESSION_PREFIX):
        return raw
    return f"{SESSION_PREFIX}{raw}"


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
        f"    {quoted} -m showwork claim --session {session} "
        "--claim \"<what changed>\" --type file_exists --path <file>\n"
        f"    {quoted} -m showwork finish --session {session} --status ok\n"
        "\n"
        "A clean close needs at least one check-backed claim. If finish exits 2, "
        "fix the file or retract the claim. Do not pass --no-verify. Do not wrap "
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


def _payload(state: str, details: dict[str, Any]) -> dict[str, Any]:
    if state not in EVIDENCE_STATES:
        state = "unknown"
    out = {"state": state, "label": LABELS[state]}
    out.update(details)
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
        state = verify_session(workspace, session)
        status = session_status(workspace, session)
        row = (status.get("sessions") or [{}])[0]
        details["verdict"] = state.get("verdict")
        details["passed"] = state.get("passed")
        details["total"] = state.get("total")
        details["claim_count"] = len(claims)
        details["open"] = bool(row.get("open"))
        details["last_status"] = row.get("last_status")
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
        failed = [r for r in checked if r.get("status") in {"fail", "error"}]
        if failed:
            first = failed[0]
            details["claim"] = first.get("claim")
            details["check"] = first.get("type")
            details["detail"] = first.get("detail")
            return _payload("failed", details)
        if has_minimum_proof(state) and state.get("verdict") == "GREEN":
            first = next((r for r in checked if r.get("status") == "pass"), {})
            details["claim"] = first.get("claim")
            details["check"] = first.get("type")
            details["detail"] = first.get("detail")
            return _payload("verified", details)
        prose = next((r for r in results if r.get("status") == "skipped"), {})
        details["claim"] = prose.get("claim") or "(no check-backed claims)"
        details["detail"] = prose.get("detail") or "done without a falsifiable check"
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

    cards = []
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
        surface = _esc(row.get("surface") or "home")
        claim = _esc(verification.get("claim") or verification.get("reason") or "No receipts yet.")
        check = _esc(verification.get("check") or "")
        detail = _esc(verification.get("detail") or verification.get("verdict") or "")
        session = _esc(verification.get("session") or "")
        cards.append(
            "<article class=\"card\" data-surface=\""
            f"{surface}\" data-state=\"{state}\">"
            f"<h3>{heading}</h3>"
            f"<details class=\"evidence\" data-state=\"{state}\" data-session=\"{session}\">"
            f"<summary class=\"badge {state}\" data-state=\"{state}\">{label}</summary>"
            "<div class=\"panel\">"
            f"<p class=\"claim\">{claim}</p>"
            f"<p class=\"check\">{check}</p>"
            f"<p class=\"detail\">{detail}</p>"
            "</div></details></article>"
        )
    body = "".join(cards)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
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
<section data-surface="home"><h2>Home</h2><div class="grid">{body}</div></section>
<section data-surface="activity"><h2>Activity</h2><div class="grid">{body}</div></section>
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
