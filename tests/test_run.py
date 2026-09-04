"""The universal wrapper: showwork run --session S -- <command>."""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from showwork.cli import main
from showwork.ledger import record_claim, resolve_root, sessions_path, start_session


def _sessions(root: Path, session: str = "w") -> list[dict]:
    path = sessions_path(root, session)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def test_run_wraps_and_records(tmp_path, capsys):
    code = main(["--root", str(tmp_path), "run", "--session", "w", "--agent", "x",
                 "--", sys.executable, "-c", "print('hi')"])
    assert code == 0
    events = _sessions(tmp_path)
    assert events[0]["event"] == "session.start"
    finish = events[-1]
    assert finish["event"] == "session.finish"
    assert finish["observed_by"] == "run-wrapper"
    assert finish["command_exit"] == 0
    assert finish["claims_verdict"] == "GREEN"


def test_run_propagates_exit_code(tmp_path):
    code = main(["--root", str(tmp_path), "run", "--session", "w",
                 "--", sys.executable, "-c", "raise SystemExit(7)"])
    assert code == 7
    assert _sessions(tmp_path)[-1]["status"] == "error"


def test_run_gate_refuses_success_with_red_claims(tmp_path, capsys):
    record_claim(tmp_path, "w", "did a thing",
                 check={"type": "file_exists", "path": "nope.txt"})
    code = main(["--root", str(tmp_path), "run", "--session", "w", "--gate",
                 "--", sys.executable, "-c", "print('all good, boss')"])
    assert code == 2
    last = _sessions(tmp_path)[-1]
    assert last["event"] == "session.finish.refused"
    assert last["claims_verdict"] == "RED"
    assert last["refuse_reason"] == "claims_red"


def test_run_gate_refuses_success_with_no_claims(tmp_path, capsys):
    code = main(["--root", str(tmp_path), "run", "--session", "empty-gate",
                 "--gate", "--", sys.executable, "-c", "print('ok')"])
    assert code == 2
    last = _sessions(tmp_path, "empty-gate")[-1]
    assert last["event"] == "session.finish.refused"
    assert last["refuse_reason"] == "no_check_backed_claims"
    assert "GATE" in capsys.readouterr().err


def test_run_without_gate_reports_but_propagates(tmp_path):
    record_claim(tmp_path, "w", "did a thing",
                 check={"type": "file_exists", "path": "nope.txt"})
    code = main(["--root", str(tmp_path), "run", "--session", "w",
                 "--", sys.executable, "-c", "print('ok')"])
    assert code == 0  # observe mode: verdict recorded, exit code untouched


def test_run_missing_command_errors(tmp_path):
    try:
        main(["--root", str(tmp_path), "run", "--session", "w", "--"])
    except SystemExit as e:
        assert "requires a command" in str(e)
    else:
        raise AssertionError("expected SystemExit")


def test_run_records_wall_clock_budget(tmp_path):
    code = main(["--root", str(tmp_path), "run", "--session", "w",
                 "--max-seconds", "2", "--", sys.executable, "-c", "print('ok')"])
    assert code == 0
    finish = _sessions(tmp_path)[-1]
    assert finish["budget_max_seconds"] == 2.0
    assert finish["budget_exceeded"] is False
    assert finish["budget_elapsed_seconds"] >= 0


def test_run_halts_when_wall_clock_budget_expires(tmp_path, capsys):
    started = time.monotonic()
    code = main(["--root", str(tmp_path), "run", "--session", "w",
                 "--max-seconds", "0.05", "--", sys.executable, "-c",
                 "import time; time.sleep(2)"])
    assert code == 2
    assert time.monotonic() - started < 1
    finish = _sessions(tmp_path)[-1]
    assert finish["status"] == "budget_exceeded"
    assert finish["budget_exceeded"] is True
    assert finish["budget_reason"] == "time"
    assert "BUDGET:" in capsys.readouterr().err


def test_run_rejects_non_positive_wall_clock_budget(tmp_path):
    try:
        main(["--root", str(tmp_path), "run", "--session", "w",
              "--max-seconds", "0", "--", sys.executable, "-c", "print('x')"])
    except SystemExit as exc:
        assert "--max-seconds must be > 0" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_linked_worktree_receipt_is_written_in_worktree(tmp_path):
    try:
        subprocess.run(["git", "--version"], check=True,
                       capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("git is required for the linked-worktree receipt test")

    origin = tmp_path / "origin"
    origin.mkdir()
    subprocess.run(["git", "init"], cwd=origin, check=True,
                   capture_output=True, text=True)
    (origin / "README.md").write_text("origin\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=origin, check=True)
    subprocess.run([
        "git", "-c", "user.name=showwork-test", "-c",
        "user.email=showwork-test@example.invalid", "commit", "-m", "init",
    ], cwd=origin, check=True, capture_output=True, text=True)
    worktree = tmp_path / "scratch-worktree"
    subprocess.run(["git", "worktree", "add", str(worktree), "HEAD"],
                   cwd=origin, check=True, capture_output=True, text=True)
    try:
        assert resolve_root(worktree) == worktree.resolve()
        start_session(worktree, "linked-worktree-test")
        receipt = (worktree / ".showwork" / "sessions" /
                   "linked-worktree-test.jsonl")
        assert receipt.is_file()
        assert not (origin / ".showwork").exists()
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)],
                       cwd=origin, check=False, capture_output=True, text=True)


def test_nested_non_git_root_stays_isolated(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    subprocess.run(["git", "init"], cwd=origin, check=True,
                   capture_output=True, text=True)
    isolated = origin / "isolated"
    isolated.mkdir()

    assert not (isolated / ".git").exists()
    assert resolve_root(isolated) == isolated.resolve()


def test_run_keep_writes_only_matching_lines(tmp_path):
    """--keep turns a whole log into the one line a claim needs."""
    code = main(["--root", str(tmp_path), "run", "--session", "w",
                 "--keep", "Tests .* passed", "--keep-as", "check",
                 "--", sys.executable, "-c",
                 "print('noise one'); print('Tests 2117 passed'); print('noise two')"])
    assert code == 0
    kept = tmp_path / ".showwork" / "artifacts" / "w" / "check.txt"
    assert kept.read_text(encoding="utf-8").splitlines() == ["Tests 2117 passed"]


def test_run_without_keep_writes_no_artifact(tmp_path):
    code = main(["--root", str(tmp_path), "run", "--session", "w",
                 "--", sys.executable, "-c", "print('hi')"])
    assert code == 0
    assert not (tmp_path / ".showwork" / "artifacts").exists()


def test_run_keep_rejects_a_bad_regex(tmp_path):
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path), "run", "--session", "w", "--keep", "([",
              "--", sys.executable, "-c", "print('hi')"])


def test_run_keep_as_cannot_escape_the_artifact_dir(tmp_path):
    """--keep-as becomes a path component; traversal must not reach the ledger."""
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path), "run", "--session", "w",
              "--keep", "hi", "--keep-as", "../../evil",
              "--", sys.executable, "-c", "print('hi')"])


def test_run_keep_as_needs_keep(tmp_path):
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path), "run", "--session", "w",
              "--keep-as", "check",
              "--", sys.executable, "-c", "print('hi')"])
