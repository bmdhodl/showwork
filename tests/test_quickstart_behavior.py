"""Behavior quickstart: broken add refuses, repair verifies, a copy reruns."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
BEHAVIOR = (ROOT / "docs" / "quickstart-behavior.md").read_text(encoding="utf-8")
PYTHON_QS = (ROOT / "docs" / "quickstart-python.md").read_text(encoding="utf-8")


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    env["SHOWWORK_COMMAND_TIMEOUT_SECONDS"] = "60"
    return env


def _run(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "showwork", "--root", str(cwd), *args],
        cwd=cwd,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=60,
    )


def _python_fences(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, re.S)


def _write_broken_walk(cwd: Path) -> tuple[str, str, str]:
    broken, runner, repaired = _python_fences(BEHAVIOR)[:3]
    (cwd / "add.py").write_text(broken, encoding="utf-8")
    (cwd / "run_tests.py").write_text(runner, encoding="utf-8")
    return broken, runner, repaired


def _declare_behavior(cwd: Path, *, name_add: bool = True) -> None:
    assert _run(cwd, ["start", "--session", "first-behavior", "--agent", "manual"]).returncode == 0
    require = _run(cwd, [
        "require", "--session", "first-behavior", "--id", "add",
        "--scope", "behavior", "--description", "add(2, 2) returns 4",
        "--type", "command", "--command-arg", "python",
        "--command-arg", "run_tests.py", "--expect-exit", "0",
        "--stdout-contains", "passed",
    ])
    assert require.returncode == 0, require.stderr
    runner = _run(cwd, [
        "claim", "--session", "first-behavior",
        "--claim", "test runner exists",
        "--type", "file_exists", "--path", "run_tests.py",
    ])
    assert runner.returncode == 0, runner.stderr
    if name_add:
        named = _run(cwd, [
            "claim", "--session", "first-behavior",
            "--claim", "add.py exists",
            "--type", "file_exists", "--path", "add.py",
        ])
        assert named.returncode == 0, named.stderr


def test_behavior_docs_use_command_require_not_file_text():
    require = next(ln for ln in BEHAVIOR.splitlines() if "showwork require --session first-behavior" in ln)
    assert "--type command" in require
    assert "{" not in require
    assert "file_exists" not in require
    assert "--path add.py" in BEHAVIOR
    assert "not a measured time" in BEHAVIOR
    assert "other inputs" in BEHAVIOR
    assert "file-exists check alone is not this walk" in BEHAVIOR


def test_behavior_walk_refuses_broken_add_then_repairs(tmp_path):
    """REGRESSION: a passing file_exists claim must not hide a failing add()."""
    _broken, _runner, repaired = _write_broken_walk(tmp_path)
    _declare_behavior(tmp_path)
    refused = _run(tmp_path, ["finish", "--session", "first-behavior", "--status", "ok"])
    assert refused.returncode == 2
    assert "REFUSED" in refused.stderr
    (tmp_path / "add.py").write_text(repaired, encoding="utf-8")
    recovered = _run(tmp_path, ["finish", "--session", "first-behavior", "--status", "ok"])
    assert recovered.returncode == 0, recovered.stderr + recovered.stdout
    assert "Outcome: VERIFIED" in recovered.stdout
    replica = tmp_path / "copy"
    shutil.copytree(tmp_path, replica)
    rerun = _run(replica, ["verify", "--session", "first-behavior", "--no-report"])
    assert rerun.returncode == 0, rerun.stderr + rerun.stdout


def test_repair_without_naming_add_py_stays_refused(tmp_path):
    """REGRESSION: repairing add.py without naming that path stays undeclared."""
    _broken, _runner, repaired = _write_broken_walk(tmp_path)
    _declare_behavior(tmp_path, name_add=False)
    refused = _run(tmp_path, ["finish", "--session", "first-behavior", "--status", "ok"])
    assert refused.returncode == 2
    (tmp_path / "add.py").write_text(repaired, encoding="utf-8")
    still = _run(tmp_path, ["finish", "--session", "first-behavior", "--status", "ok"])
    assert still.returncode == 2
    assert "undeclared change: add.py" in still.stdout


def test_behavior_walk_stays_refused_when_add_stays_broken(tmp_path):
    _write_broken_walk(tmp_path)
    _declare_behavior(tmp_path)
    first = _run(tmp_path, ["finish", "--session", "first-behavior", "--status", "ok"])
    second = _run(tmp_path, ["finish", "--session", "first-behavior", "--status", "ok"])
    assert first.returncode == 2
    assert second.returncode == 2


def test_python_behavior_walk_executes(tmp_path):
    section = PYTHON_QS.split("## Behavior walk", 1)[1]
    code = _python_fences(section)[0]
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=_env(),
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("REFUSED") >= 1 or "REFUSED" in result.stderr
    assert "Outcome: VERIFIED" in result.stdout


def test_behavior_bash_refuse_and_repair_commands_run(tmp_path):
    import shlex
    broken, runner, repaired = _python_fences(BEHAVIOR)[:3]
    (tmp_path / "add.py").write_text(broken, encoding="utf-8")
    (tmp_path / "run_tests.py").write_text(runner, encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)```", BEHAVIOR, re.S)
    refuse = blocks[2]
    repair = blocks[3]
    env = _env()
    refusals = 0
    verified = 0
    for block, add_source in ((refuse, None), (repair, repaired)):
        if add_source is not None:
            (tmp_path / "add.py").write_text(add_source, encoding="utf-8")
        for line in block.strip().splitlines():
            args = shlex.split(line)
            if args[:3] == ["python", "-m", "showwork"]:
                args = [sys.executable, "-m", "showwork", "--root", str(tmp_path), *args[3:]]
            elif args[0] == "cp" or args[0] == "cd":
                continue
            else:
                raise AssertionError(f"Unrecognized behavior command: {line}")
            result = subprocess.run(
                args, cwd=tmp_path, env=env, text=True,
                capture_output=True, timeout=60,
            )
            finish = "finish" in args
            broken_add = "+ 1" in (tmp_path / "add.py").read_text(encoding="utf-8")
            expected = 2 if finish and broken_add else 0
            assert result.returncode == expected, result.stdout + result.stderr
            refusals += "REFUSED" in result.stderr
            verified += "Outcome: VERIFIED" in result.stdout
    assert refusals == 1
    assert verified == 1


def test_behavior_powershell_flags_match_bash():
    bash = re.findall(r"```bash\n(.*?)```", BEHAVIOR, re.S)
    powershell = re.findall(r"```powershell\n(.*?)```", BEHAVIOR, re.S)
    bash_showwork = [
        "\n".join(ln for ln in block.splitlines() if "showwork" in ln)
        for block in bash
    ]
    ps_showwork = [
        "\n".join(ln for ln in block.splitlines() if "showwork" in ln)
        for block in powershell
    ]
    bash_showwork = [block for block in bash_showwork if block.strip()]
    ps_showwork = [block for block in ps_showwork if block.strip()]
    assert bash_showwork == ps_showwork
    assert "Copy-Item" in BEHAVIOR
    assert "cp -a" in BEHAVIOR


def test_behavior_walk_on_installed_package(tmp_path):
    venv = tmp_path / "venv"
    created = subprocess.run(
        [sys.executable, "-m", "venv", str(venv)],
        capture_output=True, text=True, timeout=60,
    )
    assert created.returncode == 0, created.stderr
    py = venv / ("Scripts" if sys.platform == "win32" else "bin") / (
        "python.exe" if sys.platform == "win32" else "python"
    )
    install = subprocess.run(
        [str(py), "-m", "pip", "install", "--quiet", str(ROOT)],
        capture_output=True, text=True, timeout=180,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    work = tmp_path / "work"
    work.mkdir()
    broken, runner, repaired = _python_fences(BEHAVIOR)[:3]
    (work / "add.py").write_text(broken, encoding="utf-8")
    (work / "run_tests.py").write_text(runner, encoding="utf-8")
    env = os.environ.copy()
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    env.pop("PYTHONPATH", None)

    def sw(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(py), "-m", "showwork", "--root", str(work), *args],
            cwd=work, env=env, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == expected, result.stdout + result.stderr
        return result

    sw("doctor")
    sw("start", "--session", "first-behavior", "--agent", "manual")
    sw(
        "require", "--session", "first-behavior", "--id", "add",
        "--scope", "behavior", "--description", "add(2, 2) returns 4",
        "--type", "command", "--command-arg", "python",
        "--command-arg", "run_tests.py", "--expect-exit", "0",
        "--stdout-contains", "passed",
    )
    sw(
        "claim", "--session", "first-behavior",
        "--claim", "test runner exists",
        "--type", "file_exists", "--path", "run_tests.py",
    )
    sw(
        "claim", "--session", "first-behavior",
        "--claim", "add.py exists",
        "--type", "file_exists", "--path", "add.py",
    )
    refused = sw("finish", "--session", "first-behavior", "--status", "ok", expected=2)
    assert "REFUSED" in refused.stderr
    (work / "add.py").write_text(repaired, encoding="utf-8")
    recovered = sw("finish", "--session", "first-behavior", "--status", "ok")
    assert "Outcome: VERIFIED" in recovered.stdout
    replica = tmp_path / "copy"
    shutil.copytree(work, replica)
    rerun = subprocess.run(
        [str(py), "-m", "showwork", "--root", str(replica),
         "verify", "--session", "first-behavior", "--no-report"],
        cwd=replica, env=env, capture_output=True, text=True, timeout=60,
    )
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
