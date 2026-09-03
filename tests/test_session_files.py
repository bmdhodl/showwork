"""Per-session ledger files: one writer per path, legacy files still readable."""

import hashlib
import json
import subprocess

import pytest

from showwork.audit import audit_root
from showwork.ledger import (
    claims_path,
    genesis_hash,
    load_all_claims,
    load_all_events,
    record_claim,
    record_retraction,
    session_claims_path,
    session_events_path,
    session_file_stem,
    start_session,
    verify_session,
)


def test_two_sessions_write_two_files(tmp_path):
    start_session(tmp_path, "claude-fix")
    start_session(tmp_path, "codex-fix")
    claude = session_events_path(tmp_path, "claude-fix")
    codex = session_events_path(tmp_path, "codex-fix")
    assert claude != codex
    assert claude.is_file()
    assert codex.is_file()
    record_claim(tmp_path, "claude-fix", "a")
    record_claim(tmp_path, "codex-fix", "b")
    assert session_claims_path(tmp_path, "claude-fix").is_file()
    assert session_claims_path(tmp_path, "codex-fix").is_file()
    assert session_claims_path(tmp_path, "claude-fix") != session_claims_path(
        tmp_path, "codex-fix"
    )


def test_new_writes_do_not_touch_legacy_shared_files(tmp_path):
    start_session(tmp_path, "s")
    record_claim(tmp_path, "s", "one")
    ledger = tmp_path / ".showwork"
    assert not (ledger / "sessions.jsonl").exists()
    assert not list(ledger.glob("claims-*.jsonl"))
    assert (ledger / "sessions" / "s.jsonl").is_file()
    assert (ledger / "claims" / "s.jsonl").is_file()


def test_session_file_stem_rejects_path_escape():
    with pytest.raises(ValueError):
        session_file_stem("")
    with pytest.raises(ValueError):
        session_file_stem("..")
    with pytest.raises(ValueError):
        session_file_stem(".")
    slash = session_file_stem("foo/bar")
    qmark = session_file_stem("foo?bar")
    assert slash != qmark
    assert slash.startswith("h-")
    assert qmark.startswith("h-")
    assert "foo-bar" in slash
    assert "foo-bar" in qmark
    con_stem = session_file_stem("con")
    assert con_stem.startswith("h-")
    assert "sess-con" in con_stem
    assert ".." not in session_file_stem("..\\..\\escaped")
    path = session_file_stem("a" * 200)
    assert len(path) <= 120
    assert "/" not in path
    assert "\\" not in path
    # Safe ids stay exact so existing receipts keep their paths.
    assert session_file_stem("claude-fix") == "claude-fix"
    padded = session_file_stem(" foo ")
    assert padded != session_file_stem("foo")
    assert padded.startswith("h-")
    assert session_file_stem("FOO") != session_file_stem("foo")
    foo_hashed = session_file_stem("FOO")
    assert foo_hashed.startswith("h-")
    assert foo_hashed.lower() != session_file_stem(foo_hashed).lower()
    lookalike = "foo-" + hashlib.sha256(b"FOO").hexdigest()[:10]
    assert foo_hashed.lower() != session_file_stem(lookalike).lower()
    con_txt = session_file_stem("con.txt")
    assert con_txt.startswith("h-")
    assert "sess-con" in con_txt


def test_legacy_shared_files_remain_readable(tmp_path):
    (tmp_path / "artifact.txt").write_text("ok", encoding="utf-8")
    day = claims_path(tmp_path, "2026-07-16")
    day.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "session": "old",
        "ts": "2026-07-16T01:00:00",
        "claim": "legacy proof",
        "severity": "RED",
        "check": {"type": "file_exists", "path": "artifact.txt"},
        "prev": genesis_hash(day),
    }
    day.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    events = tmp_path / ".showwork" / "sessions.jsonl"
    start = {
        "event": "session.start",
        "session": "old",
        "ts": "2026-07-16T00:00:00",
        "prev": genesis_hash(events),
    }
    events.write_text(json.dumps(start) + "\n", encoding="utf-8")
    assert any(r.get("session") == "old" for r in load_all_claims(tmp_path))
    assert any(e.get("session") == "old" for e in load_all_events(tmp_path))
    state = verify_session(tmp_path, "old")
    assert state["verdict"] == "GREEN"


def test_audit_names_nested_session_files(tmp_path):
    record_claim(tmp_path, "s", "one")
    files = [row["file"] for row in audit_root(tmp_path)["files"]]
    assert "claims/s.jsonl" in files


def test_two_agent_session_files_git_merge_without_conflict(tmp_path):
    try:
        subprocess.run(["git", "--version"], check=True,
                       capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("git is required for the session-file merge test")

    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-c", "user.name=showwork-test", "-c",
           "user.email=showwork-test@example.invalid"]
    subprocess.run([*git, "init"], cwd=repo, check=True,
                   capture_output=True, text=True)
    (repo / "README").write_text("x\n", encoding="utf-8")
    subprocess.run([*git, "add", "README"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-m", "init"], cwd=repo, check=True,
                   capture_output=True, text=True)
    base = subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo, check=True,
        capture_output=True, text=True,
    ).stdout.strip() or "master"

    subprocess.run([*git, "checkout", "-b", "agent-a"], cwd=repo, check=True,
                   capture_output=True, text=True)
    start_session(repo, "cursor-nav")
    record_claim(repo, "cursor-nav", "nav",
                 check={"type": "file_exists", "path": "README"})
    subprocess.run([*git, "add", ".showwork"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-m", "cursor"], cwd=repo, check=True,
                   capture_output=True, text=True)

    subprocess.run([*git, "checkout", base], cwd=repo, check=True,
                   capture_output=True, text=True)
    subprocess.run([*git, "checkout", "-b", "agent-b"], cwd=repo, check=True,
                   capture_output=True, text=True)
    start_session(repo, "codex-api")
    record_claim(repo, "codex-api", "api",
                 check={"type": "file_exists", "path": "README"})
    subprocess.run([*git, "add", ".showwork"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-m", "codex"], cwd=repo, check=True,
                   capture_output=True, text=True)

    subprocess.run([*git, "checkout", "agent-a"], cwd=repo, check=True,
                   capture_output=True, text=True)
    merge = subprocess.run(
        [*git, "merge", "agent-b", "-m", "merge agents"],
        cwd=repo, capture_output=True, text=True,
    )
    assert merge.returncode == 0, merge.stdout + merge.stderr
    assert (repo / ".showwork" / "claims" / "cursor-nav.jsonl").is_file()
    assert (repo / ".showwork" / "claims" / "codex-api.jsonl").is_file()
    assert (repo / ".showwork" / "sessions" / "cursor-nav.jsonl").is_file()
    assert (repo / ".showwork" / "sessions" / "codex-api.jsonl").is_file()


def test_split_session_files_honor_later_retraction(tmp_path):
    """A later retraction in a filename-first file still suppresses the claim."""
    ledger = tmp_path / ".showwork" / "claims"
    ledger.mkdir(parents=True)
    old = ledger / "z-legacy.jsonl"
    rec = {
        "session": "split-s",
        "ts": "2026-09-02T20:00:00",
        "claim": "old proof",
        "severity": "RED",
        "check": {"type": "file_exists", "path": "missing.txt"},
    }
    old.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    record_retraction(tmp_path, "split-s", "old proof", "stem remap")
    new_path = session_claims_path(tmp_path, "split-s")
    assert new_path.name < old.name
    state = verify_session(tmp_path, "split-s")
    assert state["verdict"] == "GREEN"
    live = [r for r in state["results"] if not r.get("retracted")]
    assert live == []
