"""REGRESSION: status summaries must not replay historical commands (#193)."""

import json
import subprocess

import pytest

from showwork.cli import main
from showwork.ledger import finish_session, record_claim, start_session
from showwork.outcomes import record_requirement
from showwork.report import session_status


def command_session(root, closed=True):
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "check.py").write_text(
        "from pathlib import Path\nPath('sentinel').write_text('ran')\nprint('passed')\n",
        encoding="utf-8",
    )
    start_session(root, "command-session")
    check = {"type": "command", "argv": ["python", "scripts/check.py"],
             "expect_exit": 0, "stdout_contains": "passed"}
    record_requirement(root, "command-session", "command", "script passes", "behavior", check)
    record_claim(root, "command-session", "script passes", check=check)
    if closed:
        assert finish_session(root, "command-session")[0] == 0
        (root / "sentinel").unlink()


@pytest.mark.parametrize("closed", [True, False])
def test_unscoped_status_does_not_run_command(tmp_path, capsys, closed):
    command_session(tmp_path, closed=closed)
    assert main(["--root", str(tmp_path), "status"]) == 0
    output = capsys.readouterr().out
    assert not (tmp_path / "sentinel").exists()
    assert "historical_finish=" + ("GREEN" if closed else "absent") in output
    assert "command_checks=NOT_RUN (1)" in output
    assert "current_rerun=YELLOW" in output
    assert "--session" in output


def test_unscoped_status_json_marks_command_unverified(tmp_path, capsys):
    command_session(tmp_path)
    assert main(["--root", str(tmp_path), "status", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)["sessions"][0]
    assert not (tmp_path / "sentinel").exists()
    assert row["last_claims_verdict"] == "GREEN"
    assert row["live_verdict"] == "YELLOW"
    assert row["live_passed"] == 0
    assert row["command_checks_not_run"] == 1
    assert row["gaps"][0]["type"] == "command"


def test_explicit_session_still_runs_command(tmp_path, capsys):
    command_session(tmp_path)
    assert main(["--root", str(tmp_path), "status", "--session", "command-session", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)["sessions"][0]
    assert (tmp_path / "sentinel").read_text() == "ran"
    assert row["live_verdict"] == "GREEN"
    assert row["live_passed"] == 1


@pytest.mark.parametrize("check", [
    {"type": "file_exists", "path": "data.md"},
    {"type": "file_contains", "path": "data.md", "pattern": "ready"},
    {"type": "glob_count", "pattern": "data.md", "op": "==", "n": 1},
    {"type": "frontmatter", "path": "data.md", "field": "status", "equals": "ready"},
    {"type": "git_state", "clean": True},
])
def test_unscoped_status_keeps_non_command_checks_live(tmp_path, check):
    data = tmp_path / "data.md"
    data.write_text("---\nstatus: ready\n---\nready\n", encoding="utf-8")
    if check["type"] == "git_state":
        (tmp_path / ".gitignore").write_text(".showwork/\n", encoding="utf-8")
        for args in (["init"], ["add", "data.md", ".gitignore"],
                     ["-c", "user.name=Test", "-c", "user.email=test@example.test",
                      "commit", "-m", "fixture"]):
            subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    start_session(tmp_path, "live")
    record_claim(tmp_path, "live", "current data", check=check)
    assert session_status(tmp_path)["sessions"][0]["live_verdict"] == "GREEN"
    data.unlink()
    assert session_status(tmp_path)["sessions"][0]["live_verdict"] == "RED"
