"""Read-time explanation for a verify result. Nothing here is stored.

Human text and JSON both come from `explain_state`. Formatting cannot turn a
missing or failed receipt into a verified outcome.
"""

from __future__ import annotations

import re

MAX_DETAIL = 240
MAX_ROWS = 40
RECOVERY = (
    "Repair the failed check, then rerun verify. "
    "This text does not authorize a merge or a clean close."
)
LIMITATIONS = (
    "undeclared requirements: unknown",
    "test adequacy: not assessed",
    "formatting does not change the verdict",
)

_SECRET = re.compile(
    r"(?i)(sk-[A-Za-z0-9_\-]{8,}|bearer\s+[A-Za-z0-9._\-]{8,}|api[_-]?key\s*[:=]\s*\S+)"
)
_WIN_PATH = re.compile(r"[A-Za-z]:\\[^\s\"']+")
_POSIX_ABS = re.compile(r"(?<![\w])/(?:home|Users|tmp|var|opt|usr)/[^\s\"']+")


def redact(text: object) -> str:
    """Drop secrets and machine paths from a share surface. Bound the length."""
    raw = "" if text is None else str(text)
    raw = _SECRET.sub("<secret>", raw)
    raw = _WIN_PATH.sub("<path>", raw)
    raw = _POSIX_ABS.sub("<path>", raw)
    raw = " ".join(raw.split())
    if len(raw) > MAX_DETAIL:
        return raw[: MAX_DETAIL - 1] + "…"
    return raw


def row_class(row: dict) -> str:
    """Separate a disabled or unsupported check from a real failure."""
    if row.get("policy_disabled"):
        return "disabled"
    detail = str(row.get("detail") or "")
    status = row.get("status")
    if status == "error" and "unknown check type" in detail:
        return "unsupported"
    if status == "skipped" and row.get("type") is None and "no check spec" in detail:
        return "unknown"
    if status in {"pass", "fail", "error", "skipped"}:
        return str(status)
    return "unknown"


def _lane(row: dict) -> str:
    scope = row.get("scope")
    if scope in {"behavior", "artifact"}:
        return str(scope)
    return "individual_check"


def _revision(row: dict) -> str:
    evidence = row.get("evidence")
    if not isinstance(evidence, dict):
        return "absent"
    commit = evidence.get("git_commit")
    if isinstance(commit, str) and re.fullmatch(r"[0-9a-fA-F]{7,64}", commit):
        return commit[:12]
    return "absent"


def explain_state(
    state: dict,
    *,
    observation: str = "current_rerun",
    integrity: str = "unknown",
    historical_outcome: str = "absent",
) -> dict:
    """Stable fields for one verify view. Does not write a ledger."""
    results = [row for row in (state.get("results") or []) if isinstance(row, dict)]
    rows = []
    for index, row in enumerate(results[:MAX_ROWS]):
        requirement_id = row.get("requirement_id")
        rows.append({
            "requirement": redact(row.get("claim")) if requirement_id else "absent",
            "requirement_id": requirement_id if isinstance(requirement_id, str) else None,
            "check": row.get("type") or "absent",
            "scope": _lane(row),
            "result": row_class(row),
            "observed": redact(row.get("detail")),
            "evidence_ref": (
                f"requirement:{requirement_id}" if requirement_id else f"claim:{index}"
            ),
            "revision": _revision(row),
        })
    outcome = state.get("outcome") if isinstance(state.get("outcome"), dict) else {}
    verdict = outcome.get("verdict") or "UNVERIFIED"
    if verdict not in {"VERIFIED", "UNVERIFIED"}:
        verdict = "UNVERIFIED"
    return {
        "observation": observation,
        "historical_outcome": historical_outcome,
        "check_verdict": state.get("verdict") or "unknown",
        "outcome_verdict": verdict,
        "integrity": integrity,
        "limitations": list(LIMITATIONS),
        "recovery": RECOVERY,
        "truncated": len(results) > MAX_ROWS,
        "rows": rows,
    }


def render_explanation(explanation: dict) -> str:
    """One text form of `explain_state`. The dict is the structured form."""
    lines = [
        (
            f"Observation: {explanation['observation']}. "
            f"Historical finish: {explanation['historical_outcome']}."
        ),
        (
            f"Check verdict: {explanation['check_verdict']}. "
            f"Outcome: {explanation['outcome_verdict']}. "
            f"Integrity: {explanation['integrity']}."
        ),
        "Limitations: " + "; ".join(explanation["limitations"]) + ".",
        f"Recovery: {explanation['recovery']}",
    ]
    if explanation.get("truncated"):
        lines.append("Rows truncated. The verdict still uses every row.")
    for row in explanation["rows"]:
        lines.append(
            f"  requirement:{row['requirement']} check:{row['check']} "
            f"scope:{row['scope']} result:{row['result']} "
            f"evidence:{row['evidence_ref']} revision:{row['revision']}"
        )
        if row["observed"]:
            lines.append(f"       {row['observed']}")
    return "\n".join(lines)
