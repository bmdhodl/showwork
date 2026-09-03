"""pytest plugin records a claim only when --showwork-session is set."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"


def test_plugin_records_passing_session(tmp_path):
    testdir = tmp_path / "suite"
    testdir.mkdir()
    (testdir / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("SHOWWORK_ROOT", None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest", str(testdir), "-q",
            "-p", "showwork.pytest_plugin",
            "--showwork-session", "plug",
            "--showwork-root", str(tmp_path),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((tmp_path / ".showwork" / "pytest-last.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    claims = (tmp_path / ".showwork" / "claims" / "plug.jsonl").read_text(encoding="utf-8")
    assert "pytest session passed" in claims


def test_plugin_silent_without_flag(tmp_path):
    testdir = tmp_path / "suite"
    testdir.mkdir()
    (testdir / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest", str(testdir), "-q",
            "-p", "showwork.pytest_plugin",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (tmp_path / ".showwork").exists()
