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
    http_probe    {url, expect_status, body_contains?: str}
                  # Fixed timeout, bounded response, no redirects, HTTP(S) only.
    git_state     {clean?: bool, branch?: str, commit?: hex prefix}
                  # Fixed git subcommands; at least one assertion is required.

Vacuous checks are rejected, not blessed: a regex that matches the empty
string proves nothing, and a glob count that is always true (>= 0) proves
nothing. A checker that lets an agent record a bogus "done" is worse than no
checker at all.
"""

from __future__ import annotations

import json
import os
import fnmatch
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SHELL_META = set(";|&$<>`\n\r")
MAX_GLOB_MATCHES = 100_000
MAX_GLOB_TRAVERSAL = MAX_GLOB_MATCHES

# Set in the environment of any child process spawned by a `command` check.
# If that child in turn triggers verification, nested `command` checks refuse
# to run instead of recursing forever.
VERIFYING_ENV = "SHOWWORK_VERIFYING"

# Policy switch for hostile-input contexts (CI verifying a fork PR): when set,
# `command` checks refuse to execute and report an error instead. The verdict
# honestly degrades to YELLOW ("not fully verified") rather than either
# running untrusted repo code or silently passing.
NO_COMMANDS_ENV = "SHOWWORK_NO_COMMANDS"

# Policy switch for hostile-input contexts (CI verifying a fork PR): when set,
# `http_probe` checks refuse to make network requests. Network access is an
# explicit opt-in because a claim ledger is repository-controlled input.
NO_NETWORK_ENV = "SHOWWORK_NO_NETWORK"

HTTP_TIMEOUT_S = 10
MAX_HTTP_BODY_BYTES = 1024 * 1024
GIT_TIMEOUT_S = 10

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


# A fork PR controls both the `pattern` of a file_contains claim and the file
# text it runs against. Python's `re` has no timeout, and a thread stuck in
# catastrophic backtracking cannot be killed, so the match runs in a child
# process we CAN kill. Measured: `(a+)+$` against forty 'a' characters and one
# non-matching byte does not finish. Forty bytes, one pinned CPU, until the job
# times out.
REGEX_TIMEOUT_S = 5
MAX_SCAN_BYTES = 4 * 1024 * 1024

# Runs in a bare child. It imports nothing from showwork on purpose: with the
# spawn start method a child re-imports __main__, and re-entering our own CLI
# to evaluate a regex is a trap. Pattern and text go over stdin, never argv.
_SEARCH_CHILD = """\
import json, re, sys
d = json.loads(sys.stdin.read())
try:
    sys.stdout.write(json.dumps({"found": re.search(d["p"], d["t"]) is not None}))
except re.error as e:
    sys.stdout.write(json.dumps({"error": str(e)}))
"""


def _search_bounded(pattern: str, text: str) -> tuple[str, object]:
    """`re.search` with a hard wall-clock bound.

    Returns ("ok", bool) | ("error", msg) | ("timeout", None).
    """
    payload = json.dumps({"p": pattern, "t": text})
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _SEARCH_CHILD],
            input=payload, capture_output=True, text=True,
            timeout=REGEX_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return ("timeout", None)
    if proc.returncode != 0:
        return ("error", f"regex evaluation failed: {proc.stderr.strip()[:200]}")
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        return ("error", "regex evaluation returned no verdict")
    if "error" in out:
        return ("error", out["error"])
    return ("ok", bool(out["found"]))


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
    if p.stat().st_size > MAX_SCAN_BYTES:
        return ("error",
                f"{c['path']} is larger than the {MAX_SCAN_BYTES} byte scan cap")
    text = p.read_text(encoding="utf-8-sig")  # BOM-safe
    status, result = _search_bounded(pattern, text)
    if status == "timeout":
        return ("error",
                f"/{c['pattern']}/ did not finish in {REGEX_TIMEOUT_S}s against "
                f"{c['path']}; treating an unbounded pattern as a bad claim")
    if status == "error":
        return ("error", str(result))
    found = bool(result)
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
    opening = re.match(r"\A---[ \t]*(?:\r?\n|\Z)", text)
    if opening is None:
        return ("fail", f"{c['path']} has no frontmatter")
    body = text[opening.end():]
    closing = re.search(r"(?m)^---[ \t]*(?:\r?\n|\Z)", body)
    if closing is None:
        return ("fail", f"{c['path']} has no closed frontmatter block")
    fm = body[:closing.start()]
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

def _count_glob_matches(root: Path, pattern: str) -> tuple[int, str | None]:
    try:
        normalized_parts, directory_only = _glob_parts(pattern)
        count, inspected = _bounded_glob_count(root, normalized_parts, directory_only)
    except (ValueError, OSError) as exc:
        return 0, f"invalid glob pattern {pattern!r}: {exc}"
    if inspected > MAX_GLOB_TRAVERSAL:
        return 0, (
            f"glob traversal limit exceeded: {MAX_GLOB_TRAVERSAL} for pattern "
            f"{pattern!r} after inspecting {inspected} entries"
        )
    return count, None


def _glob_parts(pattern: str) -> tuple[tuple[str, ...], bool]:
    parts = [p for p in Path(pattern).parts if p and p != "."]
    if not parts:
        raise ValueError("invalid empty glob pattern")
    directory_only = pattern.endswith("/") or (
        (os.path.sep != "/" and pattern.endswith("\\"))
    )
    return tuple(parts), directory_only


def _has_recursive_glob(parts: tuple[str, ...]) -> bool:
    return any(part == "**" for part in parts)


def _bounded_glob_count(
    root: Path,
    parts: tuple[str, ...],
    directory_only: bool,
) -> tuple[int, int]:
    """Return (match_count, traversed_entries) with a hard traversal cap."""
    if not parts:
        return 0, 0

    def _is_pattern_component(segment: str) -> bool:
        return any(ch in segment for ch in "*?[")

    def _iter_dir_entries(directory: Path):
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        is_dir = entry.is_dir()
                    except OSError as exc:  # pragma: no cover - platform-specific
                        raise OSError(f"cannot read directory entry {entry.name}: {exc}")
                    yield (entry.name, is_dir)
        except OSError as exc:
            raise OSError(f"cannot read directory {directory}: {exc}") from exc

    def walk_dir(directory: Path, idx: int, inspected: int) -> tuple[int, int]:
        if idx >= len(parts):
            return 0, inspected
        segment = parts[idx]
        if idx == len(parts) - 1:
            if not _is_pattern_component(segment):
                inspected += 1
                if inspected > MAX_GLOB_TRAVERSAL:
                    return 0, inspected
                candidate = directory / segment
                exists = candidate.exists()
                if exists:
                    if not directory_only or candidate.is_dir():
                        return 1, inspected
                return 0, inspected
            count = 0
            for name, is_dir in _iter_dir_entries(directory):
                inspected += 1
                if inspected > MAX_GLOB_TRAVERSAL:
                    return count, inspected
                if directory_only and not is_dir:
                    continue
                if fnmatch.fnmatch(name, segment):
                    count += 1
            return count, inspected
        if not _is_pattern_component(segment):
            inspected += 1
            if inspected > MAX_GLOB_TRAVERSAL:
                return 0, inspected
            child = directory / segment
            if not child.is_dir():
                return 0, inspected
            return walk_dir(child, idx + 1, inspected)
        count = 0
        for name, is_dir in _iter_dir_entries(directory):
            inspected += 1
            if inspected > MAX_GLOB_TRAVERSAL:
                return count, inspected
            if not fnmatch.fnmatch(name, segment):
                continue
            if not is_dir:
                continue
            nested_count, inspected = walk_dir(directory / name, idx + 1, inspected)
            count += nested_count
            if inspected > MAX_GLOB_TRAVERSAL:
                return count, inspected
        return count, inspected

    count, inspected = walk_dir(root, 0, 0)
    return count, inspected


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
    pattern_parts, _ = _glob_parts(pattern)
    if _has_recursive_glob(pattern_parts):
        return ("error", "glob pattern must be non-recursive in verifier context")
    n, error = _count_glob_matches(root, pattern)
    if error is not None:
        return ("error", error)
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


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep the observed response status instead of following redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_url(url) -> tuple[str, str | None]:
    if not isinstance(url, str) or url == "":
        return ("error", "http_probe.url must be a non-empty string")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url):
        return ("error", "http_probe.url must not contain whitespace or control characters")
    try:
        parsed = urllib.parse.urlsplit(url)
        hostname = parsed.hostname
        parsed.port  # Force malformed/out-of-range ports to raise ValueError.
    except ValueError as exc:
        return ("error", f"invalid http_probe.url: {exc}")
    if parsed.scheme not in ("http", "https"):
        return ("error", "http_probe.url scheme must be http or https")
    if not hostname:
        return ("error", "http_probe.url must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        return ("error", "http_probe.url must not include username or password")
    if parsed.fragment:
        return ("error", "http_probe.url must not include a fragment")
    return ("pass", None)


def chk_http_probe(c: dict, root: Path) -> tuple[str, str]:
    """GET one URL and verify its exact status plus optional UTF-8 body bytes."""
    del root  # Network evidence is intentionally independent of the project root.
    if os.environ.get(NO_NETWORK_ENV):
        return ("error", "http_probe checks disabled by SHOWWORK_NO_NETWORK "
                "(policy: do not make network requests in this context)")

    url = c.get("url")
    url_status, url_detail = _http_url(url)
    if url_status == "error":
        return ("error", url_detail or "invalid http_probe.url")

    expected = c.get("expect_status")
    if isinstance(expected, bool) or not isinstance(expected, int):
        return ("error", "http_probe.expect_status must be an integer")
    if not 100 <= expected <= 599:
        return ("error", "http_probe.expect_status must be between 100 and 599")

    if "body_contains" in c:
        needle = c["body_contains"]
        if not isinstance(needle, str) or needle == "":
            return ("error", "http_probe.body_contains must be a non-empty string")
    else:
        needle = None

    request = urllib.request.Request(url, method="GET")
    opener = urllib.request.build_opener(_NoRedirectHandler())
    try:
        response = opener.open(request, timeout=HTTP_TIMEOUT_S)
    except urllib.error.HTTPError as exc:
        # HTTP errors are still HTTP responses. This lets a claim explicitly
        # prove a deliberate 404/401/redirect without following it.
        response = exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return ("error", f"http_probe request failed: {exc}")

    try:
        body = response.read(MAX_HTTP_BODY_BYTES + 1)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return ("error", f"http_probe response read failed: {exc}")
    finally:
        response.close()

    if len(body) > MAX_HTTP_BODY_BYTES:
        return ("error", f"http_probe response body exceeds {MAX_HTTP_BODY_BYTES}-byte cap")

    actual = getattr(response, "status", None)
    if actual is None:
        actual = getattr(response, "code", None)
    if actual != expected:
        return ("fail", f"HTTP status {actual}, expected {expected}")
    if needle is not None and needle.encode("utf-8") not in body:
        return ("fail", f"HTTP body missing {needle!r}")
    detail = f"HTTP status {actual}"
    if needle is not None:
        detail += f", body has {needle!r}"
    return ("pass", detail)


def _run_git(root: Path, args: list[str]) -> tuple[str, str]:
    """Run one fixed, non-shell Git query against the declared project root."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "-c", "core.fsmonitor=false",
             "--no-optional-locks", *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ("error", f"git_state command failed: {exc}")
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "unknown Git error"
        return ("error", f"git_state command failed: {detail[:300]}")
    return ("pass", proc.stdout)


def chk_git_state(c: dict, root: Path) -> tuple[str, str]:
    """Verify selected local Git state without accepting claim-supplied argv."""
    requested = {key for key in ("clean", "branch", "commit") if key in c}
    if not requested:
        return ("error", "git_state requires at least one assertion: clean, branch, or commit")

    if "clean" in c and not isinstance(c["clean"], bool):
        return ("error", "git_state.clean must be a boolean")
    if "branch" in c and (not isinstance(c["branch"], str) or c["branch"] == ""):
        return ("error", "git_state.branch must be a non-empty string")
    expected_commit = c.get("commit")
    if "commit" in c and (
        not isinstance(expected_commit, str)
        or re.fullmatch(r"[0-9a-fA-F]{7,64}", expected_commit) is None
    ):
        return ("error", "git_state.commit must be a hexadecimal prefix of at least 7 characters")

    if "clean" in requested:
        status, output = _run_git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
        if status == "error":
            return (status, output)
        actual_clean = output == ""
        if actual_clean != c["clean"]:
            state = "clean" if actual_clean else "dirty"
            expected = "clean" if c["clean"] else "dirty"
            return ("fail", f"working tree is {state}, expected {expected}")

    if "branch" in requested:
        status, output = _run_git(root, ["branch", "--show-current"])
        if status == "error":
            return (status, output)
        actual_branch = output.strip()
        if actual_branch != c["branch"]:
            return ("fail", f"branch {actual_branch!r}, expected {c['branch']!r}")

    if "commit" in requested:
        status, output = _run_git(root, ["rev-parse", "--verify", "HEAD"])
        if status == "error":
            return (status, output)
        actual_commit = output.strip().lower()
        if not actual_commit.startswith(expected_commit.lower()):
            return ("fail", f"commit {actual_commit[:12]!r}, expected prefix {expected_commit!r}")

    details = []
    if "clean" in requested:
        details.append("clean" if c["clean"] else "dirty")
    if "branch" in requested:
        details.append(f"branch={c['branch']}")
    if "commit" in requested:
        details.append(f"commit={expected_commit}")
    return ("pass", "Git state matches: " + ", ".join(details))


CHECKERS = {
    "file_exists": chk_file_exists,
    "file_contains": chk_file_contains,
    "path_moved": chk_path_moved,
    "frontmatter": chk_frontmatter,
    "glob_count": chk_glob_count,
    "command": chk_command,
    "http_probe": chk_http_probe,
    "git_state": chk_git_state,
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
        return {**base, "type": None, "status": "skipped", "retracted": True,
                "detail": f"retracted: {record['_append_retraction_reason']}"}
    if record.get("retracted"):
        reason = str(record.get("retraction_reason", "claim retracted")).strip()
        return {**base, "type": None, "status": "skipped", "retracted": True,
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
    # A retracted claim is withdrawn, not outstanding. It can never pass, so
    # counting it in the denominator makes a clean run look incomplete. It is
    # still rendered; it just is not scored.
    scored = [r for r in results if not r.get("retracted")]
    passed = sum(1 for r in scored if r["status"] == "pass")
    return {"label": label, "verdict": verdict, "total": len(scored),
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
        # Severity says how bad a FAILURE would be and defaults to RED, so it
        # is only meaningful where the row actually failed. Printed on a pass it
        # is noise that reads as a failure.
        sev = f", {r['severity']}" if r["status"] in ("fail", "error") else ""
        lines.append(f"- {mark.get(r['status'], '??')} **{r['claim']}** "
                     f"(`{r['type']}`{sev})")
        lines.append(f"    - {r['detail']}")
    lines.append("")
    if state["gaps"]:
        lines += [f"## {len(state['gaps'])} gap(s) - a claimed 'done' is not real", ""]
        for g in state["gaps"]:
            lines.append(f"- [{g['severity']}/{g['status']}] {g['claim']} - {g['detail']}")
        lines.append("")
    return "\n".join(lines)
