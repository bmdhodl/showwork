"""Regressions reported by an actual isolated-environment user."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from showwork import __version__
from showwork.checks import chk_command, verify_claim
from showwork.cli import main
from showwork.scaffold import init_project


def test_version_works_without_subcommand_or_git_lookup(monkeypatch, capsys):
    """REGRESSION: --version failed with an internal 'cmd' error."""
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("version launched Git"))
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"showwork {__version__}"


def test_missing_subcommand_names_public_command(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--root", "."])
    assert exc.value.code == 2
    assert "required: COMMAND" in capsys.readouterr().err


@pytest.mark.parametrize("module", ["showwork", "showwork.cli"])
def test_documented_stop_command_is_not_installed_twice(tmp_path, module):
    """REGRESSION: init added a second hook to the documented .cli spelling."""
    path = tmp_path / ".claude" / "settings.json"
    path.parent.mkdir()
    original = {"permissions": {"deny": ["keep"]}, "hooks": {"Stop": [
        {"hooks": [{"type": "command", "command": f"python -m {module} stop-hook"}]},
        {"hooks": [{"type": "command", "command": "echo keep-user-hook"}]},
    ]}}
    path.write_text(json.dumps(original))
    init_project(tmp_path, cursor=False, ci=False)
    init_project(tmp_path, cursor=False, ci=False)
    assert json.loads(path.read_text()) == original


def test_execution_evidence_records_actual_locked_interpreter(tmp_path):
    """REGRESSION: evidence.argv named a Python executable never executed."""
    script = tmp_path / "runtime.py"
    script.write_text("import sys\nprint(sys.executable)\n")
    evidence = {}
    status, detail = chk_command({"type": "command", "argv": ["python3", "runtime.py"]},
                                 tmp_path, evidence=evidence)
    assert status == "pass", detail
    assert Path(evidence["argv"][0]).resolve() == Path(sys.executable).resolve()
    assert Path(evidence["argv"][1]).resolve() == script.resolve()
    assert evidence["python"] == sys.version.split()[0]


@pytest.mark.parametrize("stream", ["stderr", "stdout"])
def test_failed_command_displays_bounded_redacted_tail(tmp_path, stream):
    """REGRESSION: a real dependency error was hidden behind 'exit 1'."""
    script = tmp_path / "fail.py"
    script.write_text("import sys\n" +
                      f"print('old-prefix\\n' * 20 + 'context-a\\ncontext-b\\ncontext-c\\nNo module named pytest\\nC:\\\\private\\\\runner.py\\nsk-abcdefghijklmnop', file=sys.{stream})\n" +
                      "raise SystemExit(1)\n")
    result = verify_claim({"claim": "suite", "check": {"type": "command", "argv": ["python", "fail.py"]}}, tmp_path)
    assert result["status"] == "fail"
    assert "No module named pytest" in result["detail"]
    assert "old-prefix" not in result["detail"]
    assert "C:" not in result["detail"]
    assert "sk-abcdefghijklmnop" not in result["detail"]
    assert len(result["detail"]) < 2000
    assert "Python " + sys.version.split()[0] in result["detail"]
