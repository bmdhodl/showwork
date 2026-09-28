"""Exercise the actual action shell with a controlled verifier exit status."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _bash():
    bash = ("C:/Program Files/Git/bin/bash.exe" if os.name == "nt"
            else shutil.which("bash"))
    assert bash and Path(bash).is_file(), "Bash is required to test the Bash action"
    return bash


def _action_script(tmp_path):
    action = (ROOT / "actions/verify/action.yml").read_text(encoding="utf-8")
    # Extract the real final run block, without a YAML runtime dependency.
    script = action.rsplit("      run: |\n", 1)[1]
    script = "\n".join(line[8:] for line in script.splitlines())
    runner = tmp_path / "verify.sh"
    runner.write_text(script, encoding="utf-8")
    verifier = tmp_path / "verifier"
    verifier.write_text(
        '#!/usr/bin/env bash\nprintf "showwork outcome gate: %s\\n" "$FAKE_VERDICT"\n'
        'exit "$FAKE_CODE"\n', encoding="utf-8")
    verifier.chmod(0o755)
    return runner, verifier


def _example_verify_steps():
    """Yield (job, with-keys) for every verify step in the CI example."""
    text = (ROOT / "docs/examples/ci-verify.yml").read_text(encoding="utf-8")
    job = None
    steps = []
    keys = None
    for line in text.splitlines():
        stripped = line.strip()
        if line.startswith("  ") and not line.startswith("   ") and stripped.endswith(":"):
            job = stripped[:-1]
        if "bmdhodl/showwork/actions/verify@" in line:
            keys = set()
            steps.append((job, keys))
            continue
        if keys is not None:
            if stripped.startswith("- ") or stripped.endswith(":") and not line.startswith("          "):
                if stripped != "with:":
                    keys = None
                    continue
            if line.startswith("          ") and ":" in stripped and not stripped.startswith("#"):
                keys.add(stripped.split(":", 1)[0])
    return steps


def test_ci_example_pins_every_verify_step_to_one_selector(tmp_path):
    steps = _example_verify_steps()
    assert len(steps) >= 2, "the example should show the session and changed-since forms"
    runner, verifier = _action_script(tmp_path)
    for job, keys in steps:
        selectors = keys & {"session", "changed-since"}
        assert len(selectors) == 1, f"job {job!r} supplies {sorted(selectors)}"
        env = {**os.environ, "SW_MODE": "enforce", "SW_ROOT": ".",
               "SW_SESSION": "x" if "session" in keys else "",
               "SW_BASE": "x" if "changed-since" in keys else "",
               "SW_TRACKED": "true", "SW_LEGACY_BASELINE": "",
               "SW_ALLOW_COMMANDS": "false", "SW_ALLOW_NETWORK": "false",
               "SHOWWORK_ACTION_PY": verifier.as_posix(),
               "GITHUB_OUTPUT": (tmp_path / "outputs").as_posix(),
               "GITHUB_STEP_SUMMARY": (tmp_path / "summary").as_posix(),
               "FAKE_CODE": "0", "FAKE_VERDICT": "GREEN"}
        run = subprocess.run([str(_bash()), runner.as_posix()], env=env,
                             capture_output=True, text=True, timeout=20)
        assert run.returncode == 0, f"job {job!r}: {run.stdout}{run.stderr}"
        assert "Supply exactly one" not in run.stderr


def test_action_refuses_a_step_with_no_selector(tmp_path):
    runner, verifier = _action_script(tmp_path)
    env = {**os.environ, "SW_MODE": "enforce", "SW_ROOT": ".",
           "SW_SESSION": "", "SW_BASE": "", "SW_TRACKED": "true",
           "SW_LEGACY_BASELINE": "", "SW_ALLOW_COMMANDS": "false",
           "SW_ALLOW_NETWORK": "false", "SHOWWORK_ACTION_PY": verifier.as_posix(),
           "GITHUB_OUTPUT": (tmp_path / "outputs").as_posix(),
           "GITHUB_STEP_SUMMARY": (tmp_path / "summary").as_posix(),
           "FAKE_CODE": "0", "FAKE_VERDICT": "GREEN"}
    run = subprocess.run([str(_bash()), runner.as_posix()], env=env,
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 2
    assert "Supply exactly one of session or changed-since." in run.stderr


@pytest.mark.parametrize("mode,code,expected,result", [
    ("enforce", 0, 0, "verified"),
    ("enforce", 2, 2, "unverified"),
    ("advisory", 0, 0, "verified"),
    ("advisory", 2, 0, "unverified"),
    ("advisory", 17, 17, "error"),
    ("typo", 0, 2, None),
])
def test_action_policy_keeps_verdict_separate_from_enforcement(
        tmp_path, mode, code, expected, result):
    bash = ("C:/Program Files/Git/bin/bash.exe" if os.name == "nt"
            else shutil.which("bash"))
    assert bash and Path(bash).is_file(), "Bash is required to test the Bash action"
    action = (ROOT / "actions/verify/action.yml").read_text(encoding="utf-8")
    # Extract the real final run block, without a YAML runtime dependency.
    script = action.rsplit("      run: |\n", 1)[1]
    script = "\n".join(line[8:] for line in script.splitlines())
    runner = tmp_path / "verify.sh"
    runner.write_text(script, encoding="utf-8")
    verifier = tmp_path / "verifier"
    verifier.write_text(
        '#!/usr/bin/env bash\nprintf "showwork outcome gate: %s\\n" "$FAKE_VERDICT"\n'
        'exit "$FAKE_CODE"\n', encoding="utf-8")
    verifier.chmod(0o755)
    output = tmp_path / "outputs"
    summary = tmp_path / "summary"
    env = {**os.environ, "SW_MODE": mode, "SW_ROOT": ".",
           "SW_SESSION": "test", "SW_BASE": "", "SW_TRACKED": "true",
           "SW_LEGACY_BASELINE": "", "SW_ALLOW_COMMANDS": "false",
           "SW_ALLOW_NETWORK": "false", "SHOWWORK_ACTION_PY": verifier.as_posix(),
           "GITHUB_OUTPUT": output.as_posix(), "GITHUB_STEP_SUMMARY": summary.as_posix(),
           "FAKE_CODE": str(code), "FAKE_VERDICT": "GREEN" if code == 0 else "RED"}
    run = subprocess.run([str(bash), runner.as_posix()], env=env,
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == expected, run.stdout + run.stderr
    if result is None:
        assert "mode must be enforce or advisory" in run.stderr
        return
    assert f"result={result}" in output.read_text()
    assert f"exit-code={code}" in output.read_text()
    assert f"Mode: {mode}" in summary.read_text()
    if mode == "advisory" and code == 2:
        assert "::warning::" in run.stdout
        assert "RED" in summary.read_text()
        assert "not verified" in summary.read_text()
