"""Command deadlines must bound execution without dropping acceptance tests."""

import subprocess

import pytest

from showwork import checks


@pytest.fixture(autouse=True)
def command_environment(monkeypatch):
    monkeypatch.delenv(checks.VERIFYING_ENV, raising=False)
    monkeypatch.delenv(checks.NO_COMMANDS_ENV, raising=False)
    monkeypatch.delenv("SHOWWORK_COMMAND_TIMEOUT_SECONDS", raising=False)


def command(tmp_path, source="print('passed')\n", **fields):
    (tmp_path / "check.py").write_text(source, encoding="utf-8")
    return {"type": "command", "argv": ["python", "check.py"], **fields}


@pytest.mark.parametrize("configured,expected", [(None, 120), ("300", 300), ("3600", 3600)])
def test_command_deadline_reaches_process_and_receipt(tmp_path, monkeypatch, configured, expected):
    if configured is not None:
        monkeypatch.setenv("SHOWWORK_COMMAND_TIMEOUT_SECONDS", configured)
    seen = []

    def run(argv, **kwargs):
        seen.append(kwargs["timeout"])
        return subprocess.CompletedProcess(argv, 0, "passed\n", "")

    monkeypatch.setattr(checks, "run_process", run)
    evidence = {}
    result = checks.chk_command(command(tmp_path), tmp_path, evidence=evidence)
    assert result[0] == "pass"
    assert seen == [expected]
    assert evidence["timeout_seconds"] == expected


@pytest.mark.parametrize("value", ["", "0", "-1", "3601", "1.5", "nan", "inf", "oops"])
def test_invalid_command_deadline_never_executes(tmp_path, monkeypatch, value):
    monkeypatch.setenv("SHOWWORK_COMMAND_TIMEOUT_SECONDS", value)
    check = command(tmp_path, "from pathlib import Path\nPath('executed').touch()\n")
    result = checks.chk_command(check, tmp_path)
    assert result[0] == "error"
    assert "SHOWWORK_COMMAND_TIMEOUT_SECONDS" in result[1]
    assert not (tmp_path / "executed").exists()


def test_longer_deadline_runs_same_check_and_timeout_cannot_pass(tmp_path, monkeypatch):
    # REGRESSION: an otherwise valid full suite on fluarmn exceeded the fixed
    # deadline. Changing the limit must run the same check, never skip it.
    check = command(tmp_path, "import time\ntime.sleep(1.5)\nprint('passed')\n",
                    stdout_contains="passed")
    monkeypatch.setenv("SHOWWORK_COMMAND_TIMEOUT_SECONDS", "1")
    result = checks.chk_command(check, tmp_path)
    assert result[0] == "error"
    assert "timed out" in result[1]
    check["expect_exit"] = 124
    assert checks.chk_command(check, tmp_path)[0] == "error"
    check["expect_exit"] = 0
    monkeypatch.setenv("SHOWWORK_COMMAND_TIMEOUT_SECONDS", "5")
    assert checks.chk_command(check, tmp_path)[0] == "pass"
