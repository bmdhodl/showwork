"""Offline candidate checks use real Git refs and wheel metadata."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts/inspect_candidate.py"
spec = importlib.util.spec_from_file_location("inspect_candidate", SCRIPT)
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path / "source"
    root.mkdir()

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).strip()

    git("init", "-b", "main")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    (root / "pyproject.toml").write_text('version = "0.9.0"\n')
    git("add", ".")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")
    git("commit", "--allow-empty", "-m", "reviewed")
    sha = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", sha)
    wheel = tmp_path / "showwork-0.9.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("showwork-0.9.0.dist-info/METADATA", "Name: showwork\nVersion: 0.9.0\n")
    payload = {"verdict": "GREEN", "errors": [], "sessions": [{"verdict": "GREEN", "errors": [],
               "checks": {"verdict": "GREEN", "outcome": {"verdict": "VERIFIED"}, "results": [
                   {"requirement_id": "actual", "scope": "behavior", "status": "pass",
                    "evidence": {"git_commit": sha, "exit_code": 0}}]}}]}
    gate = tmp_path / "gate.json"
    gate.write_text(json.dumps(payload))
    return root, sha, base, wheel, gate, payload, git


def inspect(inputs, **overrides):
    root, sha, base, wheel, gate, _, _ = inputs
    arguments = dict(root=root, reviewed_sha=sha, base_sha=base, version="0.9.0",
                     wheel=wheel, gate=gate, accepted_change=True)
    arguments.update(overrides)
    return candidate.inspect_candidate(**arguments)


def test_candidate_identifies_bytes_without_publication_authority(inputs):
    packet = inspect(inputs)
    assert packet["decision"] == "candidate-for-owner-review"
    assert packet["wheel_sha256"] == candidate.digest(inputs[3])
    assert packet["publication_authorized"] is False
    assert inspect(inputs, retry_sha256=packet["wheel_sha256"])["retry"] is True
    with pytest.raises(ValueError, match="exact previously"):
        inspect(inputs, retry_sha256="a" * 64)


@pytest.mark.parametrize("fault", ["red", "wrong-revision", "failed-command", "artifact-only", "no-session",
                                   "top-errors", "boolean-exit"])
def test_candidate_refuses_bad_receipt_evidence(inputs, fault):
    data = inputs[5]
    row = data["sessions"][0]["checks"]["results"][0]
    if fault == "red":
        data["verdict"] = "RED"
    elif fault == "wrong-revision":
        row["evidence"]["git_commit"] = inputs[2]
    elif fault == "failed-command":
        row["evidence"]["exit_code"] = 1
    elif fault == "artifact-only":
        row["scope"] = "artifact"
    elif fault == "no-session":
        data["sessions"] = []
    elif fault == "top-errors":
        data["errors"] = ["contradictory gate evidence"]
    else:
        row["evidence"]["exit_code"] = False
    inputs[4].write_text(json.dumps(data))
    with pytest.raises(ValueError):
        inspect(inputs)


def test_candidate_refuses_stale_source_wrong_version_and_missing_wheel(inputs):
    with pytest.raises(ValueError, match="stale"):
        inspect(inputs, reviewed_sha=inputs[2])
    with pytest.raises(ValueError, match="metadata"):
        inspect(inputs, version="0.9.1")
    with pytest.raises(ValueError, match="missing"):
        inspect(inputs, wheel=inputs[3].with_name("missing.whl"))
    inputs[6]("update-ref", "refs/remotes/origin/main", inputs[2])
    with pytest.raises(ValueError, match="origin/main"):
        inspect(inputs)


def test_candidate_refuses_dirty_source_and_wrong_wheel_identity(inputs):
    with zipfile.ZipFile(inputs[3], "w") as archive:
        archive.writestr("showwork.dist-info/METADATA", "Name: other\nVersion: 0.9.0\n")
    with pytest.raises(ValueError, match="wheel identity"):
        inspect(inputs)
    (inputs[0] / "unreviewed.txt").write_text("change")
    with pytest.raises(ValueError, match="clean"):
        inspect(inputs)


def test_no_release_does_not_invent_artifact_checks(inputs):
    packet = inspect(inputs, accepted_change=False, wheel=None, gate=None)
    assert packet["decision"] == "no-release"
    assert packet["artifact_checks"] == "not performed"
    assert inspect(inputs, base_sha=inputs[1])["decision"] == "no-release"
    with pytest.raises(ValueError, match="cannot resume"):
        inspect(inputs, accepted_change=False, retry_sha256="a" * 64)


def test_optimized_cli_refuses_failed_check_and_writes_no_state(inputs):
    inputs[5]["verdict"] = "RED"
    inputs[4].write_text(json.dumps(inputs[5]))
    before = {p.name: p.read_bytes() for p in inputs[0].iterdir() if p.is_file()}
    proc = subprocess.run([sys.executable, "-O", str(SCRIPT), "--root", str(inputs[0]),
                           "--reviewed-sha", inputs[1], "--base-sha", inputs[2], "--version", "0.9.0",
                           "--wheel", str(inputs[3]), "--gate", str(inputs[4]), "--accepted-change"],
                          capture_output=True, text=True, timeout=30,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert proc.returncode == 2
    assert "not GREEN" in proc.stderr
    assert before == {p.name: p.read_bytes() for p in inputs[0].iterdir() if p.is_file()}


def test_candidate_accepts_real_tracked_gate_evidence(inputs):
    """REGRESSION: hand-built evidence must not substitute a different wire shape."""
    from showwork.ledger import finish_session, record_claim, start_session
    from showwork.outcomes import record_requirement, release_gate
    root, _, base, wheel, gate, _, git = inputs
    (root / "probe.py").write_text("print('passed')\n", encoding="utf-8")
    git("add", "probe.py")
    git("commit", "-m", "real probe")
    start_session(root, "candidate-proof")
    record_requirement(root, "candidate-proof", "probe", "execute the real probe", "behavior",
                       {"type": "command", "argv": ["python", "probe.py"],
                        "expect_exit": 0, "stdout_contains": "passed"})
    record_claim(root, "candidate-proof", "probe exists", {"type": "file_exists", "path": "probe.py"})
    finish_session(root, "candidate-proof", "ok")
    git("add", ".showwork")
    git("commit", "-m", "closed tracked receipt")
    sha = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", sha)
    actual = release_gate(root, "candidate-proof", require_tracked=True)
    assert actual["verdict"] == "GREEN", actual["errors"]
    row = next(row for row in actual["checks"]["results"] if row.get("scope") == "behavior")
    assert row["evidence"]["git_commit"] == sha
    gate.write_text(json.dumps({"verdict": actual["verdict"], "errors": [], "sessions": [actual]}))
    packet = candidate.inspect_candidate(root, sha, base, "0.9.0", wheel, gate, accepted_change=True)
    assert packet["decision"] == "candidate-for-owner-review"
    assert packet["gate_sha256"] == candidate.digest(gate)
