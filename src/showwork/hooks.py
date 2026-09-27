"""Adapters for agent lifecycle hooks.

Stop hooks are observers. They preserve the verification verdict at the point an
agent stops, but they never block the host process. The explicit ``finish``
command remains the gate that can refuse a false clean close.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TextIO

from .checks import gaps_payload
from .ledger import (_read_jsonl, load_all_events, record_event, session_events_path,
                     verify_session)

SESSION_ENV = "SHOWWORK_SESSION"
LATEST_START = "latest-session-start"


def read_stop_payload(stream: TextIO) -> dict:
    """Read one Claude Code/Codex-style Stop-hook payload."""
    payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError("stop-hook payload must be a JSON object")
    return payload


def payload_session_id(payload: dict) -> str:
    """Accept the session-id spellings used by common coding-agent hooks.

    Only string (or int/float) ids are used. Lists/dicts/bools must not become
    session names like ``\"['a']\"`` or ``\"True\"`` via str() — that pollutes
    the ledger and mis-attributes verify results.
    """
    raw = payload.get("session_id")
    if raw is None:
        raw = payload.get("sessionId")
    if isinstance(raw, bool) or raw is None:
        # bool is a subclass of int; never accept True/False as session ids.
        return "unknown-session"
    if isinstance(raw, (str, int, float)):
        text = str(raw).strip()
        return text or "unknown-session"
    return "unknown-session"


def resolve_stop_session(root: Path, payload: dict) -> tuple[str, str | None]:
    """Bind Stop to the agent task slug.

    Returns (session_id, bound_from). SHOWWORK_SESSION wins. Otherwise the
    hook binds to the latest started session while it is still open: a host
    hook runs with the host's environment, so an agent cannot export the
    variable to it mid-session. With neither, it falls back to the payload id
    and ``observe_stop`` stamps ``session_unbound``.
    """
    env = os.environ.get(SESSION_ENV, "").strip()
    if env:
        return env, SESSION_ENV
    active = open_latest_session(root)
    if active:
        return active, LATEST_START
    return payload_session_id(payload), None


def open_latest_session(root: Path) -> str | None:
    """The most recently started session, if no explicit close followed it.

    Stop-hook observations do not close a session; a refused finish leaves it
    open. A tie on the latest start time binds nothing rather than guess.
    """
    events = load_all_events(root)
    starts = [e for e in events if e.get("event") == "session.start"
              and isinstance(e.get("session"), str)]
    if not starts:
        return None
    latest = max(str(e.get("ts", "")) for e in starts)
    sessions = {e["session"] for e in starts if str(e.get("ts", "")) == latest}
    if len(sessions) != 1:
        return None
    session = sessions.pop()
    lifecycle = [e for e in events if e.get("session") == session
                 and e.get("event") in _LIFECYCLE
                 and e.get("observed_by") != "stop-hook"]
    if lifecycle[-1].get("event") == "session.finish":
        return None
    return session


_LIFECYCLE = frozenset({"session.start", "session.finish", "session.finish.refused"})


def observe_stop(root: Path, payload: dict, status: str = "ok") -> tuple[dict, dict]:
    """Verify the hook session and append an observed finish event.

    The returned state is informational. Callers must return success even when
    it is RED because a Stop hook observes a completed stop; it is not the
    explicit exit gate.
    """
    session, bound_from = resolve_stop_session(root, payload)
    payload_id = payload_session_id(payload)
    state = verify_session(root, session)
    unverified = gaps_payload(state)
    fields: dict = {
        "status": status,
        "observed_by": "stop-hook",
        "claims_verdict": state["verdict"],
        "claims_unverified": unverified,
    }
    if bound_from:
        fields["session_bound_from"] = bound_from
        if payload_id not in ("unknown-session", session):
            fields["hook_payload_session"] = payload_id
    else:
        # Explicit: this finish used the host id, not a task session.
        fields["session_unbound"] = True
        if payload_id != session:
            fields["hook_payload_session"] = payload_id
    # A repeat of the latest observation adds no evidence, and appending it
    # would dirty the committed ledger on every stop.
    events = _read_jsonl(session_events_path(root, session))
    if events and _same_observation(events[-1], fields):
        return events[-1], state
    event = record_event(root, "session.finish", session, **fields)
    return event, state


_VOLATILE_KEYS = frozenset({"event", "session", "ts", "prev"})


def _same_observation(last: dict, fields: dict) -> bool:
    if last.get("event") != "session.finish":
        return False
    return {k: v for k, v in last.items() if k not in _VOLATILE_KEYS} == fields
