"""README quickstart runs as pasted in an empty directory."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _run(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    return subprocess.run(
        [sys.executable, "-m", "showwork", "--root", str(cwd), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_python_module_help_and_empty_argv():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    help_proc = subprocess.run(
        [sys.executable, "-m", "showwork", "--help"],
        env=env, capture_output=True, text=True, timeout=15,
    )
    assert help_proc.returncode == 0
    assert "start" in help_proc.stdout
    empty = subprocess.run(
        [sys.executable, "-m", "showwork"],
        env=env, capture_output=True, text=True, timeout=15,
    )
    assert empty.returncode == 0
    assert "start" in empty.stdout


def test_readme_quickstart_names_the_refusal_commands():
    assert "showwork start --session first-look --agent cursor" in README
    assert "--type file_exists --path config/api.yaml" in README
    assert "showwork finish --session first-look --status ok" in README
    assert "python -m showwork" in README


def test_quickstart_refuses_false_done_in_empty_directory(tmp_path):
    start = _run(tmp_path, ["start", "--session", "first-look", "--agent", "cursor"])
    assert start.returncode == 0, start.stderr
    claim = _run(tmp_path, [
        "claim", "--session", "first-look",
        "--claim", "config/api.yaml exists",
        "--type", "file_exists", "--path", "config/api.yaml",
    ])
    assert claim.returncode == 0, claim.stderr
    finish = _run(tmp_path, ["finish", "--session", "first-look", "--status", "ok"])
    assert finish.returncode == 2
    assert "REFUSED" in finish.stderr
    assert "RED" in finish.stdout


def test_quickstart_recovery_closes_green(tmp_path):
    test_quickstart_refuses_false_done_in_empty_directory(tmp_path)
    retract = _run(tmp_path, [
        "retract", "--session", "first-look",
        "--claim", "config/api.yaml exists",
        "--reason", "file was not written yet",
    ])
    assert retract.returncode == 0, retract.stderr
    config = tmp_path / "config"
    config.mkdir()
    (config / "api.yaml").write_text("timeout: 30\n", encoding="utf-8")
    claim = _run(tmp_path, [
        "claim", "--session", "first-look",
        "--claim", "config/api.yaml exists",
        "--type", "file_exists", "--path", "config/api.yaml",
    ])
    assert claim.returncode == 0, claim.stderr
    finish = _run(tmp_path, ["finish", "--session", "first-look", "--status", "ok"])
    assert finish.returncode == 0, finish.stderr + finish.stdout
    assert "GREEN" in finish.stdout
