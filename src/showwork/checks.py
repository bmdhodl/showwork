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


def _resolve(root: Path, path_str: str) -> Path:
    resolved_root = root.resolve()
    resolved = (resolved_root / path_str).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PathEscapeError(f"path escapes project root: {path_str}") from exc
    return resolved


def chk_file_exists(c: dict, root: Path) -> tuple[str, str]:
    p = _resolve(root, c["path"])
    return ("pass", f"{c['path']} exists") if p.is_file() else ("fail", f"{c['path']} missing")


def chk_file_contains(c: dict, root: Path) -> tuple[str, str]:
    p = _resolve(root, c["path"])
    if not p.is_file():
        return ("fail", f"{c['path']} missing")
    pattern = c["pattern"]
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
    src = _resolve(root, c["from"])
    dst = _resolve(root, c["to"])
    if src.exists():
        return ("fail", f"source still exists: {c['from']}")
    if not dst.exists():
        return ("fail", f"destination missing: {c['to']}")
    return ("pass", f"{c['from']} -> {c['to']}")


def chk_frontmatter(c: dict, root: Path) -> tuple[str, str]:
    p = _resolve(root, c["path"])
    if not p.is_file():
        return ("fail", f"{c['path']} missing")
    text = p.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return ("fail", f"{c['path']} has no frontmatter")
    end = text.find("\n---", 3)
    fm = text[3:end] if end != -1 else ""
    m = re.search(rf"(?m)^{re.escape(c['field'])}\s*:\s*(.+?)\s*$", fm)
    if not m:
        return ("fail", f"field `{c['field']}` not in frontmatter")
    actual = m.group(1).strip().strip("\"'")
    want = str(c["equals"]).strip()
    return ("pass", f"{c['field']}={actual}") if actual == want \
        else ("fail", f"{c['field']}={actual}, claimed {want}")


def chk_glob_count(c: dict, root: Path) -> tuple[str, str]:
    op = c["op"]
    want = int(c["n"])
    pattern_path = Path(str(c["pattern"]))
    if pattern_path.is_absolute() or ".." in pattern_path.parts:
        return ("fail", f"glob escapes project root: {c['pattern']}")
    # Reject counts that are always true regardless of the glob result: a count
    # is never negative, so `>= 0` / `> -1` verify nothing.
    if (op == ">=" and want <= 0) or (op == ">" and want < 0):
        return ("error", f"count {op} {want} is always true (vacuous check); tighten it")
    n = sum(1 for _ in root.glob(c["pattern"]))
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
    run_argv = [sys.executable or "python", str(script), *argv[2:]]
    env = {**os.environ, VERIFYING_ENV: "1"}
    try:
        proc = subprocess.run(run_argv, capture_output=True, text=True,
                              timeout=120, cwd=str(root), env=env)
    except Exception as e:  # noqa: BLE001
        return ("error", f"command failed to run: {e}")
    expect = int(c.get("expect_exit", 0))
    if proc.returncode != expect:
        return ("fail", f"exit {proc.returncode}, expected {expect}")
    needle = c.get("stdout_contains")
    if needle and needle not in proc.stdout:
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
    severity = str(record.get("severity", "RED")).upper()
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
    if not check:
        return {**base, "type": None, "status": "skipped",
                "detail": "no check spec (non-falsifiable); recorded only"}
    ctype = check.get("type")
    fn = CHECKERS.get(ctype)
    if fn is None:
        return {**base, "type": ctype, "status": "error",
                "detail": f"unknown check type {ctype!r}"}
    try:
        status, detail = fn(check, root)
    except PathEscapeError as e:
        status, detail = "fail", str(e)
    except KeyError as e:
        status, detail = "error", f"missing arg {e}"
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
    """
    retractions: dict[tuple[str, str], str] = {}
    for record in records:
        target = record.get("retracts")
        if not record.get("retracted") or not isinstance(target, dict):
            continue
        key = (str(target.get("session", "")), str(target.get("claim", "")))
        if key == ("", ""):
            continue
        reason = str(record.get("retraction_reason", "claim retracted by later record")).strip()
        retractions[key] = reason or "claim retracted by later record"

    if not retractions:
        return records

    out: list[dict] = []
    for record in records:
        key = _record_key(record)
        if key in retractions and not (record.get("retracted") and isinstance(record.get("retracts"), dict)):
            patched = dict(record)
            patched["_append_retraction_reason"] = retractions[key]
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
