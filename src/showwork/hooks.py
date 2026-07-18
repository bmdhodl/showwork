"""Adapters for agent lifecycle hooks.

Stop hooks are observers. They preserve the verification verdict at the point an
agent stops, but they never block the host process. The explicit ``finish``
command remains the gate that can refuse a false clean close.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from .ledger import record_event, verify_session


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


def observe_stop(root: Path, payload: dict, status: str = "ok") -> tuple[dict, dict]:
    """Verify the hook session and append an observed finish event.

    The returned state is informational. Callers must return success even when
    it is RED because a Stop hook observes a completed stop; it is not the
    explicit exit gate.
    """
    session = payload_session_id(payload)
    state = verify_session(root, session)
    unverified = [
        {
            "claim": gap["claim"],
            "severity": gap["severity"],
            "status": gap["status"],
            "detail": gap["detail"],
            "type": gap["type"],
        }
        for gap in state["gaps"]
    ]
    event = record_event(
        root,
        "session.finish",
        session,
        status=status,
        observed_by="stop-hook",
        claims_verdict=state["verdict"],
        claims_unverified=unverified,
    )
    return event, state
