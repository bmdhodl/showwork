"""pytest plugin records a claim only when --showwork-session is set."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"


def run_attempt(root, source, *, slug="attempt", extra=()):
    testdir = root / "suites" / slug
    testdir.mkdir(parents=True, exist_ok=True)
    (testdir / "test_example.py").write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env.pop("SHOWWORK_ROOT", None)
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(testdir), "-q", "-p",
         "showwork.pytest_plugin", "--showwork-session", slug,
         "--showwork-root", str(root), *extra], cwd=root, env=env,
        capture_output=True, text=True, timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def latest(root, slug="attempt"):
    return json.loads((root / f".showwork/artifacts/{slug}/pytest-last.json").read_text())


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
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((tmp_path / ".showwork/artifacts/plug/pytest-last.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    claims = (tmp_path / ".showwork" / "claims" / "plug.jsonl").read_text(encoding="utf-8")
    assert "pytest session passed" in claims


def test_pytest_receipts_are_isolated_between_sessions(tmp_path):
    """REGRESSION: one shared pytest-last.json changed another session's proof."""
    from showwork.ledger import verify_session
    def finish(slug, code):
        result = run_attempt(tmp_path, f"def test_case():\n    assert {code == 0!r}\n", slug=slug)
        assert result.returncode == code, result.stdout + result.stderr
    finish("passing", 0)
    finish("failing", 1)
    assert verify_session(tmp_path, "passing")["verdict"] == "GREEN"
    assert not (tmp_path / ".showwork/pytest-last.json").exists()
    finish("passing", 1)
    finish("other", 0)
    assert verify_session(tmp_path, "passing")["verdict"] == "RED"


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
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (tmp_path / ".showwork").exists()


@pytest.mark.parametrize("codes", [(0, 1), (1, 0)])
def test_attempt_order_retains_history_and_latest_result(tmp_path, codes):
    """REGRESSION: repeated pytest invocations overwrote the only observation."""
    reports = []
    for code in codes:
        result = run_attempt(tmp_path, f"def test_case():\n    assert {code == 0!r}\n")
        assert result.returncode == code, result.stdout + result.stderr
        reports.append(latest(tmp_path))
    artifacts = tmp_path / ".showwork/artifacts/attempt"
    attempts = sorted(artifacts.glob("pytest-*.json"))
    attempts = [path for path in attempts if path.name != "pytest-last.json"
                and not path.name.endswith("-started.json")]
    assert len(attempts) == 2
    assert reports[0]["invocation_id"] != reports[1]["invocation_id"]
    for report in reports:
        retained = artifacts / f"pytest-{report['invocation_id']}.json"
        assert json.loads(retained.read_text()) == report
        assert report["status"] == "finished"
        assert report["collected"] == 1
        assert report["counts"]["passed"] == int(report["passed"])
        assert report["counts"]["failed"] == int(not report["passed"])
        start = json.loads((artifacts / f"pytest-{report['invocation_id']}-started.json").read_text())
        assert start["status"] == "running"
        assert start["passed"] is None
    assert latest(tmp_path)["exitstatus"] == codes[-1]


@pytest.mark.parametrize("source,exitstatus,count", [
    ("", 5, {}),
    ("import pytest\n@pytest.mark.skip(reason='fixture')\ndef test_case(): pass\n", 0, {"skipped": 1}),
    ("import pytest\n@pytest.fixture\ndef broken(): raise ValueError('fixture')\ndef test_case(broken): pass\n", 1, {"errors": 1}),
    ("raise ValueError('collection fixture')\n", 2, {"errors": 1}),
    ("def test_case(): raise KeyboardInterrupt()\n", 2, {}),
])
def test_exit_modes_report_only_observed_counts(tmp_path, source, exitstatus, count):
    result = run_attempt(tmp_path, source)
    assert result.returncode == exitstatus, result.stdout + result.stderr
    report = latest(tmp_path)
    assert report["exitstatus"] == exitstatus
    assert report["status"] == "finished"
    assert report["passed"] is (exitstatus == 0)
    assert report["finished_at"] >= report["started_at"]
    for name, expected in count.items():
        assert report["counts"][name] == expected
    if exitstatus != 0:
        assert report["counts"]["passed"] == 0


def test_hard_kill_cannot_leave_previous_pass_current(tmp_path):
    """REGRESSION: a killed second run left the first run's passed=true current."""
    from showwork.ledger import verify_session

    assert run_attempt(tmp_path, "def test_case(): assert True\n").returncode == 0
    first = latest(tmp_path)
    (tmp_path / "suites/attempt/test_example.py").write_text(
        "from pathlib import Path\nimport time\ndef test_case():\n"
        "    Path('entered-test').write_text('ready')\n    time.sleep(60)\n", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(SRC), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    env.pop("SHOWWORK_ROOT", None)
    proc = subprocess.Popen(
        [sys.executable, "-m", "pytest", "suites/attempt", "-q", "-p", "showwork.pytest_plugin",
         "--showwork-session", "attempt", "--showwork-root", str(tmp_path)],
        cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        deadline = time.monotonic() + 15
        while not (tmp_path / "entered-test").exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert (tmp_path / "entered-test").exists(), "Child must actually start its test"
        pending = latest(tmp_path)
        assert pending["status"] == "running"
        assert pending["invocation_id"] != first["invocation_id"]
        assert pending["passed"] is None
        assert pending["finished_at"] is None
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=10)
    assert verify_session(tmp_path, "attempt")["verdict"] == "RED"
    assert not (tmp_path / f".showwork/artifacts/attempt/pytest-{pending['invocation_id']}.json").exists()
    started = tmp_path / f".showwork/artifacts/attempt/pytest-{pending['invocation_id']}-started.json"
    before = started.read_bytes()
    assert run_attempt(tmp_path, "def test_case(): assert True\n").returncode == 0
    assert started.read_bytes() == before


def test_context_is_actual_and_arguments_are_hashed(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    (tmp_path / "seed").write_text("fixture", encoding="utf-8")
    for args in (["add", "seed"], ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                                  "commit", "-m", "fixture"]):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    head = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
    assert run_attempt(tmp_path, "def test_case(): assert True\n").returncode == 0
    report = latest(tmp_path)
    assert report["git_revision"] == head
    assert report["python_executable"] == sys.executable
    assert report["python_version"] == platform.python_version()
    assert report["pytest_version"] == pytest.__version__
    assert len(report["invocation_args_sha256"]) == 64
    assert "invocation_args" not in report


def test_artifact_pass_does_not_supply_acceptance_or_close(tmp_path):
    from showwork.ledger import verify_session
    assert run_attempt(tmp_path, "def test_case(): assert True\n").returncode == 0
    state = verify_session(tmp_path, "attempt")
    assert state["outcome"]["verdict"] == "UNVERIFIED", state
    assert state["outcome"]["total"] == 0
    env = dict(os.environ, PYTHONPATH=str(SRC))
    env.pop("SHOWWORK_ROOT", None)
    result = subprocess.run([sys.executable, "-m", "showwork", "--root", str(tmp_path),
                             "finish", "--session", "attempt", "--status", "ok"],
                            env=env, cwd=tmp_path, capture_output=True, text=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert result.returncode == 2, result.stdout + result.stderr


def test_default_hooks_do_not_probe_git_or_create_state(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from showwork import pytest_plugin
    config = SimpleNamespace(getoption=lambda option: "", rootpath=tmp_path)
    session = SimpleNamespace(config=config)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: pytest.fail("Default hook queried Git"))
    pytest_plugin.pytest_sessionstart(session)
    pytest_plugin.pytest_sessionfinish(session, 0)
    assert not hasattr(config, "_showwork_attempt")
    assert not list(tmp_path.iterdir())


def test_expected_failures_are_not_ordinary_passes_or_skips(tmp_path):
    result = run_attempt(tmp_path, "import pytest\n"
                         "@pytest.mark.xfail\ndef test_expected(): assert False\n"
                         "@pytest.mark.xfail\ndef test_unexpected(): assert True\n")
    assert result.returncode == 0, result.stdout + result.stderr
    counts = latest(tmp_path)["counts"]
    assert counts == {"passed": 0, "failed": 0, "skipped": 0, "errors": 0,
                      "xfailed": 1, "xpassed": 1}


def test_completed_attempt_corruption_is_visible(tmp_path):
    from showwork.ledger import verify_session
    assert run_attempt(tmp_path, "def test_case(): assert True\n").returncode == 0
    report = latest(tmp_path)
    artifact = tmp_path / f".showwork/artifacts/attempt/pytest-{report['invocation_id']}.json"
    corrupted = {**report, "counts": {**report["counts"], "passed": 999}}
    artifact.write_text(json.dumps(corrupted), encoding="utf-8")
    assert verify_session(tmp_path, "attempt")["verdict"] == "RED"


def test_legacy_three_field_artifact_and_claim_are_preserved(tmp_path):
    """REGRESSION: extending the adapter must not require rewriting old receipts."""
    from showwork.ledger import record_claim, verify_session

    artifacts = tmp_path / ".showwork/artifacts/attempt"
    artifacts.mkdir(parents=True)
    (artifacts / "pytest-last.json").write_text(
        json.dumps({"session": "attempt", "exitstatus": 0, "passed": True}), encoding="utf-8")
    record_claim(tmp_path, "attempt", "pytest session passed",
                 check={"type": "file_contains", "path": ".showwork/artifacts/attempt/pytest-last.json",
                        "pattern": '"passed": true'})
    legacy_claims = tmp_path / ".showwork/claims/attempt.jsonl"
    before = legacy_claims.read_bytes()
    assert verify_session(tmp_path, "attempt")["verdict"] == "GREEN"

    result = run_attempt(tmp_path, "def test_case(): assert True\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert legacy_claims.read_bytes().startswith(before)
    assert latest(tmp_path)["passed"] is True
    assert verify_session(tmp_path, "attempt")["verdict"] == "GREEN"
