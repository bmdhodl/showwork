"""Render an existing gate result for CI. Never verify or execute its records."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from urllib.parse import quote, urlsplit

from .explain import LIMITATIONS, redact, row_class
from .ledger import session_file_stem

MAX_INPUT = 2_000_000
MAX_SESSIONS = 256
MAX_REQUIREMENTS = 80
MAX_SUMMARY_BYTES = 900_000  # Leave room for the action's heading and gate verdict.


class _SummaryLines(list):
    """Stop on a complete line; retain a visible truncation notice."""

    def __init__(self, values=()):
        super().__init__()
        self.bytes = 0
        self.truncated = False
        self.extend(values)

    def append(self, value):
        size = len(value.encode("utf-8")) + 1
        if self.truncated or self.bytes + size > MAX_SUMMARY_BYTES:
            self.truncated = True
            return
        super().append(value)
        self.bytes += size

    def extend(self, values):
        for value in values:
            self.append(value)


def _text(value: object) -> str:
    value = re.sub(r"[^\s@]+@[^\s@]+", "<email>", redact(value))
    # Quotes stay: no text lands in a URL or an attribute, and [ ] ( ) block link titles.
    value = html.escape(value, quote=False)
    return re.sub(r"([\\`*_[\]()|])", r"\\\1", value)


def _revision(value: object) -> str | None:
    return value if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{40,64}", value) else None


def _base(server_url: str, repository: str, revision: str | None, route="blob") -> str | None:
    try:
        server = urlsplit(server_url)
    except ValueError:
        return None
    if (not revision or server.scheme != "https" or not server.hostname
            or server.username or server.password or server.query or server.fragment
            or not re.fullmatch(r"[A-Za-z0-9.-]+(?::[0-9]{1,5})?", server.netloc)
            or server.path not in {"", "/"}
            or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*", repository)):
        return None
    return f"{server_url.rstrip('/')}/{repository}/{route}/{revision}"


def render_summary(result: object, *, revision: str = "", repository: str = "",
                   server_url: str = "https://github.com") -> str:
    """Display all selected sessions, with bounded rows and visible missingness."""
    result = result if isinstance(result, dict) else {}
    revision = _revision(revision)
    base = _base(server_url, repository, revision)
    lines = _SummaryLines([f"Reviewed revision: {revision or 'unknown'}", "",
                           "Limitations: " + "; ".join(LIMITATIONS) + ".", ""])
    shown = Counter()
    sessions = result.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        lines.append("UNVERIFIED: No selected session receipts.")
    else:
        for item in sessions[:MAX_SESSIONS]:
            if not isinstance(item, dict):
                lines.append("UNVERIFIED: malformed session result.")
                continue
            session = str(item.get("session") or "unknown")
            path = f".showwork/sessions/{session_file_stem(session)}.jsonl"
            receipt = f"[receipt]({base}/{quote(path, safe='/')})" if base else f"`{path}`"
            checks = item.get("checks") if isinstance(item.get("checks"), dict) else {}
            outcome = checks.get("outcome") if isinstance(checks.get("outcome"), dict) else {}
            results = checks.get("results")
            rows = [row for row in results if isinstance(row, dict) and row.get("requirement_id")] if isinstance(results, list) else []
            accepted = bool(rows) and item.get("verdict") == "GREEN" and outcome.get("verdict") == "VERIFIED"
            lines.extend([f"### Session {_text(session)}", "",
                          f"Outcome: {'VERIFIED' if accepted else 'UNVERIFIED'}. "
                          f"Gate: {_text(item.get('verdict') or 'unknown')}. {receipt}.",
                          f"Historical integrity: {_text(item.get('historical_integrity') or 'unknown')}.", ""])
            if not rows:
                lines.extend(["No declared acceptance requirements. Individual claims cannot establish an outcome.", ""])
            else:
                lines.extend(["| Requirement / receipt | Scope | Result | Observed revision | Test evidence |",
                              "| --- | --- | --- | --- | --- |"])
                for row in rows[:MAX_REQUIREMENTS]:
                    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
                    observed = _revision(evidence.get("git_commit"))
                    observed_base = _base(server_url, repository, observed, route="commit")
                    version = f"[`{observed[:12]}`]({observed_base})" if observed_base else (observed or "unknown")
                    command = (f"exit {_text(evidence['exit_code'])}; "
                               f"stdout SHA256 {_text(evidence.get('stdout_sha256') or 'absent')}"
                               if "exit_code" in evidence else "not executed / evidence absent")
                    requirement = f"{_text(row['requirement_id'])}: {_text(row.get('claim'))} ({receipt})"
                    lines.append(f"| {requirement} | {_text(row.get('scope') or 'unknown')} | "
                                 f"{row_class(row)}: {_text(row.get('detail'))} | {version} | {command} |")
                if len(rows) > MAX_REQUIREMENTS:
                    lines.append(f"{len(rows) - MAX_REQUIREMENTS} more requirements omitted from display; the gate uses all requirements.")
                lines.append("")
            errors = item.get("errors")
            for error in errors[:40] if isinstance(errors, list) else []:
                line = f"- {_text(error)}"
                lines.append(line)
                shown[line] += 1
        if len(sessions) > MAX_SESSIONS:
            lines.append(f"{len(sessions) - MAX_SESSIONS} selected sessions omitted from display; consult full gate JSON.")
    # The gate copies every session error to the top level; list only the errors not shown above.
    errors = result.get("errors")
    rest = []
    for error in errors if isinstance(errors, list) else []:
        line = f"- {_text(error)}"
        if shown[line]:
            shown[line] -= 1
        else:
            rest.append(line)
    lines.extend(rest[:40])
    notes = result.get("notes")
    for note in notes[:40] if isinstance(notes, list) else []:
        lines.append(_text(note))
    notice = ("\n\nSummary truncated at the aggregate display limit; consult full gate JSON. "
              "The gate still evaluates every selected session and requirement.\n") if lines.truncated else ""
    return "\n".join(lines) + "\n" + notice


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="")
    parser.add_argument("--repository", default="")
    parser.add_argument("--server-url", default="https://github.com")
    args = parser.parse_args()
    try:
        data = sys.stdin.read(MAX_INPUT + 1)
        if len(data) > MAX_INPUT:
            raise ValueError("input too large")
        result = json.loads(data)
        print(render_summary(result, **vars(args)), end="")
    except (ValueError, TypeError, KeyError):
        print("UNVERIFIED: summary could not read the gate result; inspect the original verifier output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
