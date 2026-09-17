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


def test_readme_require_uses_flags_before_claim():
    require_at = README.find("showwork require --session first-look")
    claim_at = README.find("showwork claim --session first-look")
    assert 0 <= require_at < claim_at
    line = README[require_at:README.find("\n", require_at)]
    assert "{" not in line
    assert "--type file_exists --path config/api.yaml" in line


def test_cursor_walk_requires_before_first_claim():
    walk = (ROOT / "docs" / "walks" / "cursor.md").read_text(encoding="utf-8")
    require_at = walk.find("python -m showwork require")
    claim_at = walk.find("python -m showwork claim")
    assert 0 <= require_at < claim_at
    line = walk[require_at:walk.find("\n", require_at)]
    assert "{" not in line
    assert "--type file_exists" in line


def test_agent_prompt_requires_before_claim():
    prompt = (ROOT / "docs" / "examples" / "agent-prompt.md").read_text(encoding="utf-8")
    require_at = prompt.find("showwork require --session")
    claim_at = prompt.find("showwork claim --session")
    assert 0 <= require_at < claim_at
    line = next(ln for ln in prompt.splitlines() if "showwork require --session" in ln)
    assert "{" not in line


def test_cursor_rule_require_uses_flags():
    rule = (ROOT / "src" / "showwork" / "templates" / "cursor-rule.mdc").read_text(
        encoding="utf-8")
    require_at = rule.find("showwork require --session")
    claim_at = rule.find("showwork claim --session")
    assert 0 <= require_at < claim_at
    line = next(ln for ln in rule.splitlines() if "showwork require --session" in ln)
    assert "{" not in line
    assert "--type command" in line


def test_quickstart_refuses_false_done_in_empty_directory(tmp_path):
    start = _run(tmp_path, ["start", "--session", "first-look", "--agent", "cursor"])
    assert start.returncode == 0, start.stderr
    requirement = _run(tmp_path, ["require", "--session", "first-look", "--id", "config",
        "--description", "config/api.yaml exists", "--scope", "artifact",
        "--type", "file_exists", "--path", "config/api.yaml"])
    assert requirement.returncode == 0, requirement.stderr
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
