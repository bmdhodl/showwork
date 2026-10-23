"""init writes an honest default test contract and finish enforces it."""

from __future__ import annotations

import json

from showwork.cli import main
from showwork.contract import (
    CONTRACT_REL,
    DEFAULT_REQUIREMENT_ID,
    RUNNER_REL,
    detect_test_command,
)
from showwork.scaffold import init_project, uninstall_project


def _cli(root, *args):
    return main(["--root", str(root), *args])


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_detects_pytest_ini(tmp_path):
    _write(tmp_path / "pytest.ini", "[pytest]\n")
    found = detect_test_command(tmp_path)
    assert found is not None
    assert found.argv == ("python", "-m", "pytest")
    assert found.source == "pytest.ini"


def test_detects_pytest_from_tests_directory(tmp_path):
    _write(tmp_path / "tests" / "test_add.py", "def test_add():\n    assert 1 + 1 == 2\n")
    found = detect_test_command(tmp_path)
    assert found is not None
    assert found.argv == ("python", "-m", "pytest", "tests")
    assert found.source == "tests/"


def test_detects_pytest_from_pyproject_and_setup_cfg(tmp_path):
    _write(tmp_path / "pyproject.toml", "[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n")
    found = detect_test_command(tmp_path)
    assert found is not None
    assert found.source == "pyproject.toml"
    (tmp_path / "pyproject.toml").unlink()
    _write(tmp_path / "setup.cfg", "[tool:pytest]\ntestpaths = tests\n")
    found = detect_test_command(tmp_path)
    assert found is not None
    assert found.source == "setup.cfg"


def test_detects_npm_go_and_cargo(tmp_path):
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "node test.js"}}))
    found = detect_test_command(tmp_path)
    assert found is not None
    assert found.argv == ("npm", "test")
    (tmp_path / "package.json").unlink()
    _write(tmp_path / "go.mod", "module example.com/demo\n")
    found = detect_test_command(tmp_path)
    assert found is not None
    assert found.argv == ("go", "test", "./...")
    (tmp_path / "go.mod").unlink()
    _write(tmp_path / "Cargo.toml", "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n")
    found = detect_test_command(tmp_path)
    assert found is not None
    assert found.argv == ("cargo", "test")


def test_detects_project_runner_before_pytest(tmp_path):
    _write(tmp_path / "scripts" / "run_tests.py", "print('passed')\n")
    _write(tmp_path / "pytest.ini", "[pytest]\n")
    found = detect_test_command(tmp_path)
    assert found is not None
    assert found.argv == ("python", "scripts/run_tests.py")


def test_detects_nothing_in_empty_repo(tmp_path):
    assert detect_test_command(tmp_path) is None
    _write(tmp_path / "package.json", json.dumps({"name": "demo"}))
    assert detect_test_command(tmp_path) is None


def test_init_writes_contract_when_pytest_is_obvious(tmp_path):
    _write(tmp_path / "pytest.ini", "[pytest]\n")
    notes = init_project(tmp_path, cursor=False, claude=False, ci=False)
    joined = "\n".join(notes)
    assert "write .showwork/contract.json" in joined
    assert "default contract: python -m pytest must pass at finish" in joined
    contract = json.loads((tmp_path / CONTRACT_REL).read_text(encoding="utf-8"))
    assert contract["test_command"] == ["python", "-m", "pytest"]
    assert (tmp_path / RUNNER_REL).is_file()


def test_init_says_so_when_nothing_is_detected(tmp_path):
    notes = init_project(tmp_path, cursor=False, claude=False, ci=False)
    assert any("no obvious test command" in n for n in notes)
    assert not (tmp_path / CONTRACT_REL).exists()
    assert not (tmp_path / RUNNER_REL).exists()


def test_init_is_idempotent(tmp_path):
    _write(tmp_path / "tests" / "test_add.py", "def test_add():\n    assert 1 + 1 == 2\n")
    first = init_project(tmp_path, cursor=False, claude=False, ci=False)
    contract = (tmp_path / CONTRACT_REL).read_bytes()
    runner = (tmp_path / RUNNER_REL).read_bytes()
    second = init_project(tmp_path, cursor=False, claude=False, ci=False)
    assert any(n.startswith("skip .showwork/contract.json") for n in second)
    assert any(n.startswith("skip .showwork/run_default_check.py") for n in second)
    assert (tmp_path / CONTRACT_REL).read_bytes() == contract
    assert (tmp_path / RUNNER_REL).read_bytes() == runner
    assert any("write .showwork/contract.json" in n for n in first)


def test_init_does_not_overwrite_user_contract_without_force(tmp_path):
    _write(tmp_path / "pytest.ini", "[pytest]\n")
    init_project(tmp_path, cursor=False, claude=False, ci=False)
    custom = '{"version": 1, "test_command": ["python", "mine.py"], "detected_from": "hand"}\n'
    (tmp_path / CONTRACT_REL).write_text(custom, encoding="utf-8")
    notes = init_project(tmp_path, cursor=False, claude=False, ci=False)
    assert any("skip .showwork/contract.json (exists; pass --force)" in n for n in notes)
    assert (tmp_path / CONTRACT_REL).read_text(encoding="utf-8") == custom
    init_project(tmp_path, cursor=False, claude=False, ci=False, force=True)
    rewritten = json.loads((tmp_path / CONTRACT_REL).read_text(encoding="utf-8"))
    assert rewritten["test_command"] == ["python", "-m", "pytest"]


def test_init_preview_does_not_write_contract(tmp_path):
    _write(tmp_path / "pytest.ini", "[pytest]\n")
    notes = init_project(tmp_path, cursor=False, claude=False, ci=False, preview=True)
    assert any(n.startswith("would write .showwork/contract.json") for n in notes)
    assert not (tmp_path / CONTRACT_REL).exists()


def test_uninstall_removes_unchanged_contract_and_keeps_edits(tmp_path):
    _write(tmp_path / "pytest.ini", "[pytest]\n")
    init_project(tmp_path, cursor=False, claude=False, ci=False)
    uninstall_project(tmp_path, cursor=False, claude=False, ci=False)
    assert not (tmp_path / CONTRACT_REL).exists()
    init_project(tmp_path, cursor=False, claude=False, ci=False)
    (tmp_path / CONTRACT_REL).write_text(
        '{"version": 1, "test_command": ["python", "mine.py"], "detected_from": "hand"}\n',
        encoding="utf-8",
    )
    notes = uninstall_project(tmp_path, cursor=False, claude=False, ci=False)
    assert any("keep .showwork/contract.json (edited)" in n for n in notes)
    assert (tmp_path / CONTRACT_REL).is_file()


def test_cli_init_prints_the_declared_contract(tmp_path, capsys):
    _write(tmp_path / "pytest.ini", "[pytest]\n")
    assert _cli(tmp_path, "init", "--cursor") == 0
    output = capsys.readouterr().out
    assert "default contract: python -m pytest must pass at finish" in output
    assert "Next: start a session and close with finish --status ok." in output


def test_no_contract_finish_refuses_instead_of_faking_pass(tmp_path, capsys):
    assert _cli(tmp_path, "init") == 0
    assert "no obvious test command" in capsys.readouterr().out
    assert not (tmp_path / CONTRACT_REL).exists()
    assert _cli(tmp_path, "start", "--session", "empty") == 0
    assert _cli(tmp_path, "finish", "--session", "empty", "--status", "ok") == 2
    assert "REFUSED" in capsys.readouterr().err


def test_init_then_failing_test_refuses_and_passing_test_verifies(tmp_path, capsys):
    _write(tmp_path / "pytest.ini", "[pytest]\n")
    _write(tmp_path / "tests" / "test_add.py",
           "from add import add\n\ndef test_add():\n    assert add(1, 1) == 2\n")
    assert _cli(tmp_path, "init") == 0
    assert _cli(tmp_path, "start", "--session", "demo", "--agent", "cursor") == 0
    assert _cli(tmp_path, "finish", "--session", "demo", "--status", "ok") == 2
    refused = capsys.readouterr()
    assert "REFUSED" in refused.err
    events = [
        json.loads(line)
        for line in (tmp_path / ".showwork" / "sessions" / "demo.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    requirement = next(row for row in events if row.get("event") == "session.requirement")
    assert requirement["requirement_id"] == DEFAULT_REQUIREMENT_ID
    assert requirement["check"]["argv"] == ["python", RUNNER_REL]
    # New implementation file: not an undeclared edit of a start-snapshot path.
    _write(tmp_path / "add.py", "def add(a, b):\n    return a + b\n")
    assert _cli(tmp_path, "finish", "--session", "demo", "--status", "ok") == 0
    assert "Outcome: VERIFIED" in capsys.readouterr().out
