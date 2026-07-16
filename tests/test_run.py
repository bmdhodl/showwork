"""The universal wrapper: showwork run --session S -- <command>."""

import json
import sys
from pathlib import Path

from showwork.cli import main
from showwork.ledger import record_claim


def _sessions(root: Path) -> list[dict]:
    path = root / ".showwork" / "sessions.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


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
    assert _sessions(tmp_path)[-1]["claims_verdict"] == "RED"


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
