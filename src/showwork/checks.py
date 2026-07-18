"""Deterministic checkers for falsifiable agent claims.

Observability tools log what an agent DID. showwork verifies what an agent
CLAIMED it did. An agent (or its harness) appends structured, falsifiable
claims to an append-only ledger; verification checks each claim against
reality and refuses to bless a "done" that is not real.

Only falsifiable, structured claims are verified. Free-form prose carries no
`check` spec and is recorded but skipped: we do not judge prose, we check
facts.

Check types:
    file_exists   {path}
    file_contains {path, pattern (regex), absent?: bool}
    path_moved    {from, to}                  # from must be gone, to must exist
    frontmatter   {path, field, equals}       # YAML frontmatter field equality
    glob_count    {pattern, op (==|>=|<=|>|<), n}
    command       {argv: [...], expect_exit?: 0, stdout_contains?: str}
                  # LOCKED: `python <script under the project root>` only.
                  # No shell, no metacharacters, no `..` escape, no PowerShell.

Vacuous checks are rejected, not blessed: a regex that matches the empty
string proves nothing, and a glob count that is always true (>= 0) proves
nothing. A checker that lets an agent record a bogus "done" is worse than no
checker at all.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

SHELL_META = set(";|&$<>`\n\r")

# Set in the environment of any child process spawned by a `command` check.
# If that child in turn triggers verification, nested `command` checks refuse
# to run instead of recursing forever.
VERIFYING_ENV = "SHOWWORK_VERIFYING"

# Policy switch for hostile-input contexts (CI verifying a fork PR): when set,
# `command` checks refuse to execute and report an error instead. The verdict
# honestly degrades to YELLOW ("not fully verified") rather than either
# running untrusted repo code or silently passing.
NO_COMMANDS_ENV = "SHOWWORK_NO_COMMANDS"

EXIT_BY_VERDICT = {"GREEN": 0, "YELLOW": 3, "RED": 2}


# ---------- per-type checkers: return (status, detail) ----------
# status in {"pass", "fail", "error"}.


class PathEscapeError(ValueError):
    """A claim tried to use evidence outside the declared project root."""


class PathArgError(ValueError):
    """A claim path field is missing, empty, or not a string."""


def _resolve(root: Path, path_str: str) -> Path:
    if not isinstance(path_str, str) or path_str.strip() == "":
        raise PathArgError(
            f"path must be a non-empty string, got {path_str!r}"
        )
    resolved_root = root.resolve()
    resolved = (resolved_root / path_str).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PathEscapeError(f"path escapes project root: {path_str}") from exc
    return resolved


def chk_file_exists(c: dict, root: Path) -> tuple[str, str]:
    p = _resolve(root, c["path"])
    if p.is_file():
        return ("pass", f"{c['path']} exists")
    if p.exists():
        return ("fail", f"{c['path']} is not a regular file")
    return ("fail", f"{c['path']} missing")


def chk_file_contains(c: dict, root: Path) -> tuple[str, str]:
    p = _resolve(root, c["path"])
    if not p.is_file():
        if p.exists():
            return ("fail", f"{c['path']} is not a regular file")
        return ("fail", f"{c['path']} missing")
    pattern = c["pattern"]
    if not isinstance(pattern, str):
        return ("error", f"pattern must be a string, got {type(pattern).__name__}")
    want_absent = bool(c.get("absent"))
    # A pattern that matches the empty string (e.g. "", "^", "$", ".*") matches
    # ANY text, so a positive file_contains claim using it always passes. It
    # verifies nothing and lets an agent record a bogus "done". Reject it as a
    # bad claim rather than bless the lie.
    try:
        matches_empty = re.search(pattern, "") is not None
    except re.error as e:
        return ("error", f"invalid regex /{pattern}/: {e}")
    if matches_empty and not want_absent:
        return ("error", f"pattern /{pattern}/ matches any text (vacuous check); tighten it")
    text = p.read_text(encoding="utf-8-sig")  # BOM-safe
    found = re.search(pattern, text) is not None
    if want_absent:
        return ("pass", f"/{c['pattern']}/ absent as claimed") if not found \
            else ("fail", f"/{c['pattern']}/ present but claimed absent")
    return ("pass", f"/{c['pattern']}/ found in {c['path']}") if found \
        else ("fail", f"/{c['pattern']}/ NOT in {c['path']}")


def chk_path_moved(c: dict, root: Path) -> tuple[str, str]:
    # Empty path strings resolve to the project root under Path join, so a
    # claim like {from: "gone", to: ""} would pass whenever the root exists.
    # That is a vacuous false proof — reject empty from/to before resolve.
    for key in ("from", "to"):
        val = c.get(key)
        if not isinstance(val, str) or val.strip() == "":
            return ("error", f"path_moved.{key} must be a non-empty path string")
    src = _resolve(root, c["from"])
    dst = _resolve(root, c["to"])
    if src.exists():
        return ("fail", f"source still exists: {c['from']}")
    if not dst.exists():
        return ("fail", f"destination missing: {c['to']}")
    return ("pass", f"{c['from']} -> {c['to']}")



def _frontmatter_equals_str(value) -> str:
    """Normalize a check `equals` value for scalar comparison.

    CLI `--equals` always supplies strings. `--check-json` may supply JSON
    booleans/null; str(True) is 'True', which never matches YAML `true`.
    Map bool/None to JSON/YAML-ish lowercase scalars; leave other values as
    stripped strings (quotes trimmed for parity with the file side).
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value).strip().strip("\"'")


def chk_frontmatter(c: dict, root: Path) -> tuple[str, str]:
    p = _resolve(root, c["path"])
    if not p.is_file():
        if p.exists():
            return ("fail", f"{c['path']} is not a regular file")
        return ("fail", f"{c['path']} missing")
    text = p.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return ("fail", f"{c['path']} has no frontmatter")
    end = text.find("\n---", 3)
    fm = text[3:end] if end != -1 else ""
    field = c["field"]
    if not isinstance(field, str) or field == "":
        return ("error", f"field must be a non-empty string, got {type(field).__name__}")
    m = re.search(rf"(?m)^{re.escape(field)}\s*:\s*(.+?)\s*$", fm)
    if not m:
        return ("fail", f"field `{field}` not in frontmatter")
    actual = m.group(1).strip().strip("\"'")
    want = _frontmatter_equals_str(c["equals"])
    return ("pass", f"{field}={actual}") if actual == want \
        else ("fail", f"{field}={actual}, claimed {want}")


def chk_glob_count(c: dict, root: Path) -> tuple[str, str]:
    op = c["op"]
    raw_n = c.get("n")
    if isinstance(raw_n, bool) or raw_n is None:
        return ("error", f"glob_count.n must be an integer, got {type(raw_n).__name__}")
    if isinstance(raw_n, int):
        want = raw_n
    else:
        try:
            want = int(raw_n)
            if isinstance(raw_n, float) and float(want) != float(raw_n):
                return ("error", f"glob_count.n must be an integer, got {raw_n!r}")
        except (TypeError, ValueError):
            return ("error", f"glob_count.n must be an integer, got {raw_n!r}")
    pattern = c.get("pattern")
    if not isinstance(pattern, str) or pattern == "":
        return ("error", "glob pattern must be a non-empty string")
    pattern_path = Path(pattern)
    if pattern_path.is_absolute() or ".." in pattern_path.parts:
        return ("fail", f"glob escapes project root: {pattern}")
    # Reject counts that are always true regardless of the glob result: a count
    # is never negative, so `>= 0` / `> -1` verify nothing.
    if (op == ">=" and want <= 0) or (op == ">" and want < 0):
        return ("error", f"count {op} {want} is always true (vacuous check); tighten it")
    try:
        n = sum(1 for _ in root.glob(pattern))
    except ValueError as e:
        return ("error", f"invalid glob pattern {pattern!r}: {e}")
    ok = {
        "==": n == want, ">=": n >= want, "<=": n <= want,
        ">": n > want, "<": n < want,
    }.get(op)
    if ok is None:
        return ("error", f"bad op {op!r}")
    return ("pass", f"count {n} {op} {want}") if ok else ("fail", f"count {n} !{op} {want}")


def chk_command(c: dict, root: Path) -> tuple[str, str]:
    """Run a LOCKED command. Only `python <script under the project root>`,
    no shell, no metacharacters, no `..` escape. A ledger data file must never
    be able to run arbitrary commands."""
    if os.environ.get(NO_COMMANDS_ENV):
        return ("error", "command checks disabled by SHOWWORK_NO_COMMANDS "
                         "(policy: do not execute repo code in this context)")
    if os.environ.get(VERIFYING_ENV):
        return ("error", "nested command verification refused (recursion guard)")
    argv = c.get("argv")
    if not isinstance(argv, list) or not argv:
        return ("error", "command.argv must be a non-empty list")
    if any((not isinstance(t, str)) or (set(t) & SHELL_META) for t in argv):
        return ("error", "command contains a non-string or shell metacharacter")
    argv0_name = Path(argv[0]).name.lower()
    if argv0_name in ("powershell", "powershell.exe", "pwsh", "pwsh.exe") \
            or any(a.lower().endswith(".ps1") for a in argv):
        return ("error", "shell scripts are locked; command must invoke a python script")
    if argv0_name not in ("python", "python.exe", "python3"):
        return ("error", "command must invoke python")
    if len(argv) < 2:
        return ("error", "command needs a script path")
    script = (root / argv[1]).resolve()
    try:
        script.relative_to(root.resolve())
    except ValueError:
        return ("error", f"script must live under the project root: {argv[1]}")
    if not script.is_file():
        return ("error", f"script not found: {argv[1]}")
    raw_expect = c.get("expect_exit", 0)
    if isinstance(raw_expect, bool) or (
        not isinstance(raw_expect, int)
        and not (isinstance(raw_expect, str) and raw_expect.strip().lstrip("-").isdigit())
    ):
        return ("error", f"expect_exit must be an integer, got {raw_expect!r}")
    try:
        expect = int(raw_expect)
    except (TypeError, ValueError):
        return ("error", f"expect_exit must be an integer, got {raw_expect!r}")
    run_argv = [sys.executable or "python", str(script), *argv[2:]]
    env = {**os.environ, VERIFYING_ENV: "1"}
    try:
        proc = subprocess.run(run_argv, capture_output=True, text=True,
                              timeout=120, cwd=str(root), env=env)
    except Exception as e:  # noqa: BLE001
        return ("error", f"command failed to run: {e}")
    if proc.returncode != expect:
        return ("fail", f"exit {proc.returncode}, expected {expect}")
    needle = c.get("stdout_contains")
    if needle is not None and needle != "":
        if not isinstance(needle, str):
            return ("error",
                    f"stdout_contains must be a string, got {type(needle).__name__}")
        if needle not in proc.stdout:
            return ("fail", f"stdout missing {needle!r}")
    return ("pass", f"exit {proc.returncode}"
            + (f", stdout has {needle!r}" if needle else ""))


CHECKERS = {
    "file_exists": chk_file_exists,
    "file_contains": chk_file_contains,
    "path_moved": chk_path_moved,
    "frontmatter": chk_frontmatter,
    "glob_count": chk_glob_count,
    "command": chk_command,
}


# ---------- verification driver ----------


def verify_claim(record: dict, root: Path) -> dict:
    claim = record.get("claim", "(no description)")
    # SPEC: severity is RED or YELLOW. Anything else (empty, GREEN, typos)
    # must not demote a failed claim out of the exit gate — default to RED.
    raw_sev = record.get("severity", "RED")
    severity = str(raw_sev if raw_sev is not None else "RED").upper().strip()
    if severity not in ("RED", "YELLOW"):
        severity = "RED"
    check = record.get("check")
    base = {"claim": claim, "session": record.get("session", ""),
            "severity": severity}
    if record.get("_parse_error"):
        # A corrupt ledger line is never harmless: it could be a real claim.
        return {**base, "type": None, "status": "error",
                "detail": f"unparseable ledger line: {record['_parse_error']}"}
    if record.get("_append_retraction_reason"):
        return {**base, "type": None, "status": "skipped",
                "detail": f"retracted: {record['_append_retraction_reason']}"}
    if record.get("retracted"):
        reason = str(record.get("retraction_reason", "claim retracted")).strip()
        return {**base, "type": None, "status": "skipped",
                "detail": f"retracted: {reason or 'claim retracted'}"}
    if check is None:
        return {**base, "type": None, "status": "skipped",
                "detail": "no check spec (non-falsifiable); recorded only"}
    if not isinstance(check, dict):
        return {**base, "type": None, "status": "error",
                "detail": f"check must be a JSON object, got {type(check).__name__}"}
    ctype = check.get("type")
    fn = CHECKERS.get(ctype)
    if fn is None:
        return {**base, "type": ctype, "status": "error",
                "detail": f"unknown check type {ctype!r}"}
    try:
        status, detail = fn(check, root)
    except PathEscapeError as e:
        status, detail = "fail", str(e)
    except PathArgError as e:
        status, detail = "error", str(e)
    except KeyError as e:
        status, detail = "error", f"missing arg {e}"
    except TypeError as e:
        # Bad field types (non-string paths, etc.) — surface the message cleanly.
        status, detail = "error", str(e)
    except Exception as e:  # noqa: BLE001
        status, detail = "error", f"checker raised: {e}"
    return {**base, "type": ctype, "status": status, "detail": detail}


def _record_key(record: dict) -> tuple[str, str]:
    return (str(record.get("session", "")), str(record.get("claim", "")))


def apply_append_retractions(records: list[dict]) -> list[dict]:
    """Honor later append-only retraction records without rewriting history.

    Inline retractions (`"retracted": true` on the claim itself) still work.
    This form lets the ledger keep the original bad claim and append a later
    record that identifies it:
        {"retracted": true, "retracts": {"session": "...", "claim": "..."},
         "retraction_reason": "..."}

    A retraction suppresses only *prior* targets in ledger order. A later
    re-claim with the same session+claim text is a new live claim and is not
    permanently killed by an earlier retraction.
    """
    # (index, key, reason) for each referencing retraction, in file order.
    events: list[tuple[int, tuple[str, str], str]] = []
    for i, record in enumerate(records):
        target = record.get("retracts")
        if not record.get("retracted") or not isinstance(target, dict):
            continue
        key = (str(target.get("session", "")), str(target.get("claim", "")))
        if key == ("", ""):
            continue
        reason = str(record.get("retraction_reason", "claim retracted by later record")).strip()
        events.append((i, key, reason or "claim retracted by later record"))

    if not events:
        return records

    out: list[dict] = []
    for i, record in enumerate(records):
        # Referencing retraction markers are bookkeeping; leave them untouched
        # (evaluate_records drops them from the active claim list separately).
        if record.get("retracted") and isinstance(record.get("retracts"), dict):
            out.append(record)
            continue
        key = _record_key(record)
        reason = None
        for j, rkey, rreason in events:
            # Only a retraction that appears *after* this record can suppress it.
            if j > i and rkey == key:
                reason = rreason
                break
        if reason is not None:
            patched = dict(record)
            patched["_append_retraction_reason"] = reason
            out.append(patched)
        else:
            out.append(record)
    return out


def evaluate_records(records: list[dict], root: Path, label: str = "") -> dict:
    """Verify a list of claim records. Verdict: any failed RED claim => RED;
    any other failure or checker error => YELLOW; else GREEN."""
    records = apply_append_retractions(records)
    # Retraction markers are bookkeeping, not claims; do not list them.
    claims = [r for r in records
              if not (r.get("retracted") and isinstance(r.get("retracts"), dict))]
    results = [verify_claim(r, root) for r in claims]
    fails = [r for r in results if r["status"] == "fail"]
    errors = [r for r in results if r["status"] == "error"]
    red = [r for r in fails if r["severity"] == "RED"]
    if red:
        verdict = "RED"
    elif fails or errors:
        verdict = "YELLOW"
    else:
        verdict = "GREEN"
    gaps = [{"claim": r["claim"], "severity": r["severity"], "status": r["status"],
             "detail": r["detail"], "type": r["type"]}
            for r in results if r["status"] in ("fail", "error")]
    passed = sum(1 for r in results if r["status"] == "pass")
    return {"label": label, "verdict": verdict, "total": len(results),
            "passed": passed, "results": results, "gaps": gaps}


def render_report(state: dict) -> str:
    lines = [f"# Claims audit - {state['label']}", "",
             f"**Verdict: {state['verdict']}**  "
             f"({state['passed']}/{state['total']} verified)", ""]
    if not state["results"]:
        lines += ["No claims recorded.", ""]
        return "\n".join(lines)
    mark = {"pass": "OK", "fail": "XX", "error": "!!", "skipped": ".."}
    for r in state["results"]:
        lines.append(f"- {mark.get(r['status'], '??')} **{r['claim']}** "
                     f"(`{r['type']}`, {r['severity']})")
        lines.append(f"    - {r['detail']}")
    lines.append("")
    if state["gaps"]:
        lines += [f"## {len(state['gaps'])} gap(s) - a claimed 'done' is not real", ""]
        for g in state["gaps"]:
            lines.append(f"- [{g['severity']}/{g['status']}] {g['claim']} - {g['detail']}")
        lines.append("")
    return "\n".join(lines)
