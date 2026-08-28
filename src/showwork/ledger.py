"""Append-only claims ledger and session lifecycle.

Layout (under the project root):
    .showwork/
      claims-YYYY-MM-DD.jsonl   one claim record per line, append-only
      sessions.jsonl            session.start / session.finish events

Records are never rewritten. Corrections are append-only retractions that
reference the original claim, so the ledger stays a faithful history of what
was asserted, when, and what was later withdrawn.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from .checks import evaluate_records, gaps_payload

LEDGER_DIRNAME = ".showwork"
ROOT_ENV = "SHOWWORK_ROOT"
GENESIS_PREFIX = "showwork:genesis:"
# Ledger day files are claims-YYYY-MM-DD.jsonl only. Reject anything else so a
# hostile --date cannot turn claims_path into a multi-segment escape.
_CLAIMS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Appends are usually serialized within one agent process. Cache the last
# record hash for that hot path, while using file metadata to notice an append
# from another process and fall back to the full, correctness-first scan.
# The cache is an optimization only: audit remains the authority for ledger
# integrity, and a changed file that is not noticed by the filesystem still
# produces a broken chain on the next audit.
_PREV_HASH_CACHE: dict[Path, tuple[int, int, str]] = {}


def resolve_root(root: str | Path | None = None) -> Path:
    """Resolve a project root, anchoring linked worktrees to their origin.

    A linked worktree has a worktree-specific ``git-dir`` but shares its
    ``git-common-dir`` with the origin checkout. Receipts must live in the
    origin checkout so deleting the worktree cannot delete the audit trail.
    Non-git temporary directories remain valid roots for isolated tests and
    standalone use cases.
    """
    if root:
        candidate = Path(root).resolve()
    else:
        env = os.environ.get(ROOT_ENV)
        candidate = Path(env).resolve() if env else Path.cwd().resolve()
    if not candidate.exists():
        return candidate

    git_marker = candidate / ".git"
    if not git_marker.exists():
        return candidate
    try:
        show_top = _git_value(candidate, "--show-toplevel")
        git_dir = _git_value(candidate, "--git-dir")
        common_dir = _git_value(candidate, "--git-common-dir")
    except (FileNotFoundError, subprocess.CalledProcessError, OSError) as exc:
        # Preserve non-git roots such as pytest's tmp_path. A linked worktree
        # has a .git file; if Git cannot resolve it, fail before writing.
        if git_marker.is_file():
            raise RuntimeError(
                f"cannot resolve origin repository for worktree {candidate}: {exc}"
            ) from exc
        return candidate

    top = Path(show_top).resolve()
    git_dir_path = _resolve_git_path(git_dir, top)
    common_dir_path = _resolve_git_path(common_dir, top)
    if git_dir_path == common_dir_path:
        return top

    origin = common_dir_path.parent.resolve()
    if not origin.is_dir():
        raise RuntimeError(
            f"origin repository is unavailable for worktree {candidate}: {origin}"
        )
    try:
        origin_top = Path(_git_value(origin, "--show-toplevel")).resolve()
    except (FileNotFoundError, subprocess.CalledProcessError, OSError) as exc:
        raise RuntimeError(
            f"origin repository is unavailable for worktree {candidate}: {origin}"
        ) from exc
    if origin_top != origin:
        raise RuntimeError(
            f"origin repository path mismatch for worktree {candidate}: "
            f"expected {origin}, got {origin_top}"
        )
    return origin


def _git_value(root: Path, flag: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", flag],
        check=True,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if not value:
        raise RuntimeError(f"git rev-parse {flag} returned no path for {root}")
    return value


def _resolve_git_path(value: str, base: Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def ledger_dir(root: Path) -> Path:
    return resolve_root(root) / LEDGER_DIRNAME


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def claims_path(root: Path, date_str: str | None = None) -> Path:
    """Path to a day's claims file. ``date_str`` MUST be YYYY-MM-DD when set.

    Unvalidated dates were joined as ``claims-{date}.jsonl``; values containing
    ``..`` / separators resolved outside ``.showwork/``.
    """
    label = date_str if date_str is not None else _today()
    if not _CLAIMS_DATE_RE.fullmatch(str(label)):
        raise ValueError(f"claims date must be YYYY-MM-DD, got {date_str!r}")
    base = ledger_dir(root).resolve()
    path = (base / f"claims-{label}.jsonl").resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"claims path escapes ledger dir: {date_str!r}") from exc
    return path


def sessions_path(root: Path) -> Path:
    return ledger_dir(root) / "sessions.jsonl"


def line_hash(line: str) -> str:
    """SHA-256 of one record line's content. EOL-agnostic on purpose: the
    hash covers the stripped line, so an editor or checkout that only
    rewrites line endings does not break the chain, while any content
    change does."""
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()


def genesis_hash(path: Path) -> str:
    """Anchor for the first record of a ledger file."""
    return hashlib.sha256((GENESIS_PREFIX + path.name).encode("utf-8")).hexdigest()


# --- record framing (shared with showwork.audit and js/showwork-audit) ---
#
# All three readers must agree byte-for-byte on where one record ends and the
# next begins, so the split rule and the JSON dialect live here and nowhere
# else. See SPEC.md, "Storage and framing".

_RECORD_SEP = re.compile(r"\r?\n")


def read_record_text(path: Path) -> str:
    r"""Read a ledger file as text with the BOM stripped and newlines left
    untranslated. ``Path.read_text`` opens in universal-newline mode, which
    folds a lone CR (and CRLF) into ``\n`` *before* any split runs — silently
    re-introducing the very segmentation divergence ``split_record_lines``
    exists to kill, since the JS auditor reads raw bytes and never translates.
    Reading bytes and decoding with ``utf-8-sig`` strips the BOM and keeps
    every ``\r`` and ``\n`` intact, so ``\r?\n`` is the *only* boundary rule.

    Raises ``ValueError`` (not bare ``UnicodeDecodeError``) when the file is
    not valid UTF-8 so verify/audit/append can surface a clear non-GREEN result
    or a clear write failure instead of an uncaught codec exception.
    """
    try:
        return path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError(f"ledger file {path.name} is not valid UTF-8: {e}") from e


def split_record_lines(text: str) -> list[str]:
    r"""Segment a ledger file into physical lines on LF or CRLF only, matching
    the JS auditor's ``text.split(/\r?\n/)``. Deliberately *not*
    ``str.splitlines()``: that also breaks on U+2028, U+2029, U+0085, VT, FF,
    the FS/GS/RS/US controls, and a lone CR — none of which a ``JSON.parse``
    reader treats as a boundary. Splitting on those would cut a JSON string
    that legitimately contains one, so the implementations would disagree on
    record counts, head hashes, and the line a break is reported at.
    Feed it text from ``read_record_text`` so newlines are untranslated."""
    return _RECORD_SEP.split(text)


def _reject_nonfinite(literal: str) -> float:
    """``json.loads`` calls this for the bare tokens ``NaN``, ``Infinity``, and
    ``-Infinity``. They are not valid JSON and ``JSON.parse`` rejects them, so
    raise to make both implementations treat such a line as a parse error (a
    pre-chain/YELLOW record), never a live record with a numeric ``prev``."""
    raise ValueError(f"non-standard JSON constant {literal!r}")


def strict_json_loads(line: str):
    """Parse one record line in the strict JSON dialect the JS auditor enforces:
    ``NaN``/``Infinity``/``-Infinity`` are parse errors, not values. Raises
    ``ValueError`` (``json.JSONDecodeError`` is a subclass) on any
    non-conforming line."""
    return json.loads(line, parse_constant=_reject_nonfinite)


def _record_lines(path: Path) -> list[str]:
    """The record lines of a ledger file: BOM-safe, blank and comment lines
    skipped, exactly the framing the reader uses."""
    if not path.is_file():
        return []
    lines = []
    for line in split_record_lines(read_record_text(path)):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def _prev_hash(path: Path) -> str:
    key = path.resolve()
    try:
        stat = path.stat()
    except FileNotFoundError:
        return genesis_hash(path)
    cached = _PREV_HASH_CACHE.get(key)
    fingerprint = (stat.st_size, stat.st_mtime_ns)
    if cached and cached[:2] == fingerprint:
        return cached[2]
    lines = _record_lines(path)
    previous = line_hash(lines[-1]) if lines else genesis_hash(path)
    _PREV_HASH_CACHE[key] = (*fingerprint, previous)
    return previous


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record["prev"] = _prev_hash(path)
    line = json.dumps(record, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    stat = path.stat()
    _PREV_HASH_CACHE[path.resolve()] = (stat.st_size, stat.st_mtime_ns, line_hash(line))


def _read_jsonl(path: Path) -> list[dict]:
    """BOM-safe, comment-tolerant JSONL reader. Unparseable lines become
    YELLOW records instead of being silently dropped. Invalid UTF-8 becomes a
    single YELLOW error record instead of raising."""
    if not path.is_file():
        return []
    try:
        text = read_record_text(path)
    except ValueError as e:
        return [{"claim": f"(unreadable ledger file {path.name})",
                 "check": None, "_parse_error": str(e),
                 "severity": "YELLOW"}]
    records: list[dict] = []
    for i, line in enumerate(split_record_lines(text), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = strict_json_loads(line)
        except ValueError as e:
            records.append({"claim": f"(unparseable line {i} in {path.name})",
                            "check": None, "_parse_error": str(e),
                            "severity": "YELLOW"})
            continue
        if not isinstance(obj, dict):
            records.append({
                "claim": f"(non-object line {i} in {path.name})",
                "check": None,
                "_parse_error": f"expected JSON object, got {type(obj).__name__}",
                "severity": "YELLOW",
            })
            continue
        records.append(obj)
    return records


# ---------- writing ----------


def record_claim(root: Path, session: str, claim: str, check: dict | None = None,
                 severity: str = "RED", artifact: str | None = None) -> dict:
    rec: dict = {"session": session, "ts": _now(), "claim": claim,
                 "severity": severity.upper()}
    if check:
        rec["check"] = check
    if artifact:
        rec["artifact"] = artifact
    _append(claims_path(root), rec)
    return rec


def record_retraction(root: Path, session: str, claim: str, reason: str) -> dict:
    rec = {"session": session, "ts": _now(), "retracted": True,
           "retracts": {"session": session, "claim": claim},
           "retraction_reason": reason}
    _append(claims_path(root), rec)
    return rec


def record_event(root: Path, event: str, session: str, **fields) -> dict:
    rec = {"event": event, "session": session, "ts": _now()}
    rec.update({k: v for k, v in fields.items() if v is not None})
    _append(sessions_path(root), rec)
    return rec


# ---------- reading ----------


def load_claims(root: Path, date_str: str | None = None) -> list[dict]:
    return _read_jsonl(claims_path(root, date_str))


def load_all_claims(root: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(ledger_dir(root).glob("claims-*.jsonl")):
        records.extend(_read_jsonl(path))
    return records


def claims_for_session(root: Path, session: str) -> list[dict]:
    out = []
    for r in load_all_claims(root):
        if r.get("session") == session:
            out.append(r)
        elif isinstance(r.get("retracts"), dict) and r["retracts"].get("session") == session:
            out.append(r)
    return out


# ---------- verification entry points ----------


def verify_date(root: str | Path | None = None, date_str: str | None = None) -> dict:
    rt = resolve_root(root)
    label = date_str or _today()
    return evaluate_records(load_claims(rt, label), rt, label=label)


def verify_session(root: str | Path | None = None, session: str = "") -> dict:
    rt = resolve_root(root)
    return evaluate_records(claims_for_session(rt, session), rt,
                            label=f"session {session}")


# ---------- session lifecycle ----------


def start_session(root: Path, session: str, agent: str | None = None,
                  note: str | None = None) -> dict:
    return record_event(root, "session.start", session, agent=agent, note=note)


def finish_session(root: Path, session: str, status: str = "ok",
                   no_verify: bool = False, note: str | None = None) -> tuple[int, dict | None]:
    """Close a session. A clean close (`status=ok`) verifies this session's own
    claims first and REFUSES (exit 2) if any is RED: a green exit with a red
    ledger is not done. A clean close also REFUSES when the session has no
    check-backed claims (prose-only or empty is not proof). `status=blocked` or
    `no_verify=True` closes without gating, and the bypass is stamped on the
    event as a durable residual.

    Status is matched case-insensitively (`OK` == `ok`) so the Python API cannot
    silently skip the gate with a capitalization variant.
    """
    status_norm = str(status or "").strip().lower()
    if status_norm not in ("ok", "blocked"):
        raise ValueError(f"status must be 'ok' or 'blocked', got {status!r}")
    status = status_norm
    state = None
    verdict = None
    if status == "ok" and not no_verify:
        state = verify_session(root, session)
        verdict = state["verdict"]
        live_checked = [r for r in state["results"] if r["status"] != "skipped"]
        refuse_reason = None
        unverified = gaps_payload(state)
        if not live_checked:
            refuse_reason = "no_check_backed_claims"
            verdict = "RED"
            unverified = [{
                "claim": "(session has no check-backed claims)",
                "severity": "RED",
                "status": "fail",
                "detail": "clean close needs at least one falsifiable claim that verifies",
                "type": None,
            }]
        elif verdict == "RED":
            refuse_reason = "claims_red"
        if refuse_reason is not None:
            record_event(root, "session.finish.refused", session,
                         status=status, claims_verdict=verdict, note=note,
                         refuse_reason=refuse_reason,
                         claims_unverified=unverified)
            if refuse_reason == "no_check_backed_claims" and state is not None:
                # Surface the refuse reason on the returned state for CLI/tests.
                state = dict(state)
                state["verdict"] = "RED"
                state["gaps"] = unverified
                state["refuse_reason"] = refuse_reason
            return 2, state
    record_event(root, "session.finish", session, status=status,
                 claims_verdict=verdict,
                 verify_bypassed=(True if (no_verify and status == "ok") else None),
                 note=note)
    return 0, state
