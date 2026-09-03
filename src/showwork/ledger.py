"""Append-only claims ledger and session lifecycle.

Layout (under the project root):
    .showwork/
      sessions/<id>.jsonl       session.start / session.finish for one session
      claims/<id>.jsonl         claims and retractions for one session
      claims-YYYY-MM-DD.jsonl   legacy shared day file (read, not written)
      sessions.jsonl            legacy shared session file (read, not written)

New writes go to per-session files so two agents never share a path.
Readers still load the legacy files. Records are never rewritten.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from .checks import evaluate_records, gaps_payload, validate_check_shape

LEDGER_DIRNAME = ".showwork"
ROOT_ENV = "SHOWWORK_ROOT"
GENESIS_PREFIX = "showwork:genesis:"
# Ledger day files are claims-YYYY-MM-DD.jsonl only. Reject anything else so a
# hostile --date cannot turn claims_path into a multi-segment escape.
_CLAIMS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SESSION_STEM_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
_SESSION_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_WINDOWS_RESERVED = frozenset({
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
})

# Appends are usually serialized within one agent process. Cache the last
# record hash for that hot path, while using file metadata to notice an append
# from another process and fall back to the full, correctness-first scan.
# The cache is an optimization only: audit remains the authority for ledger
# integrity, and a changed file that is not noticed by the filesystem still
# produces a broken chain on the next audit.
_PREV_HASH_CACHE: dict[Path, tuple[int, int, str]] = {}


def resolve_root(root: str | Path | None = None) -> Path:
    """Resolve a project root to the checkout that will commit the receipt.

    Linked worktrees keep their own working tree. Receipts live there so they
    ship with the branch. Two agents in two worktrees then write two paths.
    Non-git temporary directories remain valid roots for isolated tests.
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
    except (FileNotFoundError, subprocess.CalledProcessError, OSError) as exc:
        # Preserve non-git roots such as pytest's tmp_path. A linked worktree
        # has a .git file; if Git cannot resolve it, fail before writing.
        if git_marker.is_file():
            raise RuntimeError(
                f"cannot resolve git toplevel for {candidate}: {exc}"
            ) from exc
        return candidate

    return Path(show_top).resolve()


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


def session_file_stem(session: str) -> str:
    """Turn a session id into a single path component.

    Two agents that share a slug still collide. Distinct slugs must map to
    distinct files: when sanitization or truncation would collide distinct
    inputs, prefix the stem with h- and a short hash of the original id so
    the stem stays injective.
    Empty ids, path separators, and Windows reserved device names are rejected
    or rewritten, never joined.
    """
    original = session if session is not None else ""
    raw = original.strip()
    if not raw:
        raise ValueError("session id is empty")
    if raw in {".", ".."}:
        raise ValueError(f"session id is not a safe file stem: {session!r}")
    cleaned = _SESSION_UNSAFE_RE.sub("-", raw).strip(".-")
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    base = cleaned.split(".")[0].lower()
    if cleaned.lower() in _WINDOWS_RESERVED or base in _WINDOWS_RESERVED:
        cleaned = f"sess-{cleaned}"
    digest = hashlib.sha256(original.encode("utf-8")).hexdigest()[:10]
    # Lossy when whitespace was stripped, characters were rewritten, reserved
    # names were prefixed, case differs, or the id was truncated.
    # Hashed stems live under h- so they cannot collide with an exact id,
    # including a lowercase id that looks like "{cleaned}-{digest}".
    lossy = cleaned != raw or len(raw) > 120 or original != raw or cleaned != cleaned.lower() or cleaned.lower().startswith("h-")
    if lossy:
        base = cleaned.lower()
        prefix = f"h-{digest}-"
        max_base = 120 - len(prefix)
        if len(base) > max_base:
            base = base[:max_base].rstrip(".-")
        cleaned = f"{prefix}{base}" if base else f"h-{digest}"
    if not cleaned or cleaned in {".", ".."} or not _SESSION_STEM_RE.fullmatch(cleaned):
        raise ValueError(f"session id is not a safe file stem: {session!r}")
    return cleaned


def has_minimum_proof(state: dict) -> bool:
    """True when the verify state has at least one non-skipped check result."""
    return any(r.get("status") != "skipped" for r in state.get("results", []))


def _session_subdir_path(root: Path, subdir: str, session: str) -> Path:
    base = ledger_dir(root).resolve()
    folder = (base / subdir).resolve()
    path = (folder / f"{session_file_stem(session)}.jsonl").resolve()
    try:
        path.relative_to(folder)
        folder.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"session ledger path escapes ledger dir: {session!r}") from exc
    return path


def session_claims_path(root: Path, session: str) -> Path:
    return _session_subdir_path(root, "claims", session)


def session_events_path(root: Path, session: str) -> Path:
    return _session_subdir_path(root, "sessions", session)


def ledger_dir(root: Path) -> Path:
    return resolve_root(root) / LEDGER_DIRNAME


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def claims_path(root: Path, date_str: str | None = None) -> Path:
    """Path to a legacy day file. ``date_str`` MUST be YYYY-MM-DD when set.

    New claims write to ``session_claims_path``. This path remains for
    ``verify --date`` against historical day files and for tests that seed
    them. Unvalidated dates were joined as ``claims-{date}.jsonl``; values
    containing ``..`` / separators resolved outside ``.showwork/``.
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


def sessions_path(root: Path, session: str | None = None) -> Path:
    """Per-session events file, or the legacy shared file when session is None."""
    if session is not None:
        return session_events_path(root, session)
    return ledger_dir(root) / "sessions.jsonl"


def iter_claim_paths(root: Path) -> list[Path]:
    """Legacy day files plus per-session claim files, in a stable order."""
    directory = ledger_dir(root)
    files: list[Path] = []
    if directory.is_dir():
        files.extend(sorted(directory.glob("claims-*.jsonl")))
        claims_dir = directory / "claims"
        if claims_dir.is_dir():
            files.extend(sorted(claims_dir.glob("*.jsonl")))
    return files


def iter_session_event_paths(root: Path) -> list[Path]:
    """Legacy shared sessions file plus per-session event files."""
    directory = ledger_dir(root)
    files: list[Path] = []
    legacy = directory / "sessions.jsonl"
    if legacy.is_file():
        files.append(legacy)
    sessions_dir = directory / "sessions"
    if sessions_dir.is_dir():
        files.extend(sorted(sessions_dir.glob("*.jsonl")))
    return files


def iter_ledger_jsonl(root: Path) -> list[Path]:
    """Every chained JSONL under the ledger, including spec-v0.2 leftovers."""
    seen: set[Path] = set()
    files: list[Path] = []
    for path in [*iter_claim_paths(root), *iter_session_event_paths(root)]:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(path)
    return files


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
    # None is prose (no check). Any explicit value, including {}, is a check
    # and must pass shape validation. Do not use truthiness: {} is falsy.
    if check is not None:
        shape_err = validate_check_shape(check, root)
        if shape_err is not None:
            raise ValueError(shape_err)
    rec: dict = {"session": session, "ts": _now(), "claim": claim,
                 "severity": severity.upper()}
    if check is not None:
        rec["check"] = check
    if artifact:
        rec["artifact"] = artifact
    _append(session_claims_path(root, session), rec)
    return rec


def record_retraction(root: Path, session: str, claim: str, reason: str) -> dict:
    rec = {"session": session, "ts": _now(), "retracted": True,
           "retracts": {"session": session, "claim": claim},
           "retraction_reason": reason}
    _append(session_claims_path(root, session), rec)
    return rec


def record_event(root: Path, event: str, session: str, **fields) -> dict:
    rec = {"event": event, "session": session, "ts": _now()}
    rec.update({k: v for k, v in fields.items() if v is not None})
    _append(session_events_path(root, session), rec)
    return rec


# ---------- reading ----------


def load_claims(root: Path, date_str: str | None = None) -> list[dict]:
    """Claims for one calendar day.

    The matching legacy day file is loaded in full (records with no ``ts``
    stay there). Per-session files contribute records whose ``ts`` starts
    with that YYYY-MM-DD label.
    """
    label = date_str if date_str is not None else _today()
    if not _CLAIMS_DATE_RE.fullmatch(str(label)):
        raise ValueError(f"claims date must be YYYY-MM-DD, got {date_str!r}")
    records: list[dict] = []
    daily = claims_path(root, label)
    daily_key = daily.resolve() if daily.is_file() else None
    if daily.is_file():
        records.extend(_read_jsonl(daily))
    for path in iter_claim_paths(root):
        if daily_key is not None and path.resolve() == daily_key:
            continue
        file_recs = _read_jsonl(path)
        dated: list[dict] = []
        errors: list[dict] = []
        for rec in file_recs:
            ts = rec.get("ts")
            if isinstance(ts, str) and ts.startswith(str(label)):
                dated.append(rec)
            if rec.get("_parse_error"):
                errors.append(rec)
        records.extend(dated)
        if dated:
            records.extend(errors)
            continue
        if not errors:
            continue
        try:
            mtime_day = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        except OSError:
            continue
        if mtime_day == str(label):
            records.extend(errors)
    return records


def load_all_claims(root: Path) -> list[dict]:
    records: list[dict] = []
    for path in iter_claim_paths(root):
        records.extend(_read_jsonl(path))
    return records


def load_all_events(root: Path) -> list[dict]:
    records: list[dict] = []
    for path in iter_session_event_paths(root):
        records.extend(_read_jsonl(path))
    return records


def claims_for_session(root: Path, session: str) -> list[dict]:
    out = []
    for r in load_all_claims(root):
        if r.get("session") == session:
            out.append(r)
        elif isinstance(r.get("retracts"), dict) and r["retracts"].get("session") == session:
            out.append(r)
    path = session_claims_path(root, session)
    if path.is_file():
        for r in _read_jsonl(path):
            if r.get("_parse_error"):
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
    `no_verify=True` closes without gating. `--no-verify` stamps
    `verify_bypassed` on an `ok` close. A blocked close still verifies and
    stamps `claims_verdict` so FDR does not treat it as a clean close.

    Status is matched case-insensitively (`OK` == `ok`) so the Python API cannot
    silently skip the gate with a capitalization variant.
    """
    status_norm = str(status or "").strip().lower()
    if status_norm not in ("ok", "blocked"):
        raise ValueError(f"status must be 'ok' or 'blocked', got {status!r}")
    status = status_norm
    state = None
    verdict = None
    if not no_verify:
        state = verify_session(root, session)
        verdict = state["verdict"]
    if status == "ok" and not no_verify:
        refuse_reason = None
        unverified = gaps_payload(state)
        if not has_minimum_proof(state):
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
