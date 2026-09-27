"""Exercise the actual action shell with a controlled verifier exit status."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


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
