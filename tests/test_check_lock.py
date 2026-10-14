"""Locked checks and the tests_intact gate, end to end in a sample repository.

The sample runner prints "passed" whatever the tests hold, as a runner does
after an agent weakened them. Only the lock and the tests_intact requirement
stand between that runner and a clean close.
"""

import json
import subprocess

from showwork.cli import main
from showwork.ledger import record_event, verify_session
from showwork.receipts import receipts_payload
from showwork.reader import inspect_session

TESTS = """\
import pytest
from calc import add


def test_add():
    assert add(1, 2) == 3
    assert add(0, 0) == 0


def test_add_negative():
    assert add(-1, -1) == -2
"""


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _repo(tmp_path):
    root = tmp_path / "sample"
    (root / "tests").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "tests" / "test_calc.py").write_text(TESTS, encoding="utf-8")
    (root / "tests" / "conftest.py").write_text("collect_ignore = []\n", encoding="utf-8")
    (root / "scripts" / "run_tests.py").write_text("print('2 passed')\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


def _cli(root, *args):
    return main(["--root", str(root), *args])


def _owner_locks(root, session, *paths):
    assert _cli(root, "start", "--session", session) == 0
    assert _cli(root, "require", "--session", session, "--id", "suite", "--scope", "behavior",
                "--description", "the suite passes", "--type", "command",
                "--command-arg", "python", "--command-arg", "scripts/run_tests.py",
                "--expect-exit", "0", "--stdout-contains", "passed") == 0
    assert _cli(root, "require", "--session", session, "--id", "intact", "--scope", "artifact",
                "--description", "tests were not weakened", "--type", "tests_intact",
                "--path", "tests") == 0
    lock = ["lock", "--session", session]
    for path in paths:
        lock += ["--path", path]
    assert _cli(root, *lock) == 0


def _claim_edit(root, session, path, pattern):
    assert _cli(root, "claim", "--session", session, "--claim", f"edited {path}",
                "--type", "file_contains", "--path", path, "--pattern", pattern) == 0


def _last_event(root, session):
    lines = (root / ".showwork" / "sessions" / f"{session}.jsonl").read_text(encoding="utf-8").splitlines()
    return json.loads(lines[-1])


def test_honest_session_that_adds_tests_passes(tmp_path):
    root = _repo(tmp_path)
    _owner_locks(root, "honest", "tests/conftest.py")
    test_file = root / "tests" / "test_calc.py"
    test_file.write_text(TESTS.replace("    assert add(0, 0) == 0\n",
                                       "    assert add(0, 0) == 0\n    assert add(2, 2) == 4\n")
                         + "\n\ndef test_add_large():\n    assert add(10**6, 1) == 1000001\n",
                         encoding="utf-8")
    _claim_edit(root, "honest", "tests/test_calc.py", "test_add_large")
    assert _cli(root, "finish", "--session", "honest", "--status", "ok") == 0
    close = _last_event(root, "honest")
    assert close["event"] == "session.finish" and close["outcome"]["verdict"] == "VERIFIED"
    assert close["lock_check"]["status"] == "intact"
    assert close["lock_check"]["files"] == 2


def test_deleted_test_is_refused(tmp_path, capsys):
    root = _repo(tmp_path)
    _owner_locks(root, "delete")
    test_file = root / "tests" / "test_calc.py"
    test_file.write_text(TESTS.split("\n\ndef test_add_negative")[0] + "\n", encoding="utf-8")
    _claim_edit(root, "delete", "tests/test_calc.py", "test_add")
    assert _cli(root, "finish", "--session", "delete", "--status", "ok") == 2
    refused = _last_event(root, "delete")
    assert refused["event"] == "session.finish.refused"
    assert refused["refuse_reason"] == "tests_weakened"
    assert "test deleted: tests/test_calc.py::test_add_negative" in json.dumps(refused["claims_unverified"])
    assert "tests_weakened" in capsys.readouterr().err


def test_deleted_test_file_is_refused(tmp_path):
    root = _repo(tmp_path)
    _owner_locks(root, "delete-file")
    (root / "tests" / "test_calc.py").unlink()
    _claim_edit(root, "delete-file", "calc.py", "def add")
    assert _cli(root, "finish", "--session", "delete-file", "--status", "ok") == 2
    refused = _last_event(root, "delete-file")
    assert "test file deleted: tests/test_calc.py (2 tests)" in json.dumps(refused["claims_unverified"])


def test_added_skip_marker_is_refused(tmp_path):
    root = _repo(tmp_path)
    _owner_locks(root, "skip")
    test_file = root / "tests" / "test_calc.py"
    test_file.write_text(TESTS.replace("def test_add_negative", "@pytest.mark.skip\ndef test_add_negative"),
                         encoding="utf-8")
    _claim_edit(root, "skip", "tests/test_calc.py", "mark.skip")
    assert _cli(root, "finish", "--session", "skip", "--status", "ok") == 2
    refused = _last_event(root, "skip")
    assert refused["refuse_reason"] == "tests_weakened"
    assert "test newly skipped or xfail: tests/test_calc.py::test_add_negative" in json.dumps(
        refused["claims_unverified"])


def test_edited_locked_check_is_refused_even_when_claimed(tmp_path, capsys):
    root = _repo(tmp_path)
    _owner_locks(root, "edit-runner")
    (root / "scripts" / "run_tests.py").write_text("print('99 passed')\n", encoding="utf-8")
    _claim_edit(root, "edit-runner", "scripts/run_tests.py", "99 passed")
    assert _cli(root, "finish", "--session", "edit-runner", "--status", "ok") == 2
    refused = _last_event(root, "edit-runner")
    assert refused["refuse_reason"] == "locked_checks_changed"
    assert refused["lock_check"]["findings"] == ["locked check file changed: scripts/run_tests.py"]
    assert "locked_checks_changed" in capsys.readouterr().err


def test_locked_glob_refuses_changed_deleted_and_new_files(tmp_path):
    root = _repo(tmp_path)
    (root / "tests" / "fixtures").mkdir()
    (root / "tests" / "fixtures" / "a.json").write_text("{}", encoding="utf-8")
    _owner_locks(root, "glob", "tests/conftest.py", "tests/fixtures/**")
    (root / "tests" / "conftest.py").write_text("collect_ignore = ['test_calc.py']\n", encoding="utf-8")
    (root / "tests" / "fixtures" / "a.json").unlink()
    (root / "tests" / "fixtures" / "b.json").write_text("{}", encoding="utf-8")
    findings = verify_session(root, "glob")["lock"]["findings"]
    assert findings == ["locked check file changed: tests/conftest.py",
                        "locked check file deleted: tests/fixtures/a.json",
                        "new file under a locked path: tests/fixtures/b.json"]


def test_lock_tolerates_crlf_checkout(tmp_path):
    root = _repo(tmp_path)
    _owner_locks(root, "crlf", "tests/conftest.py")
    conftest = root / "tests" / "conftest.py"
    conftest.write_bytes(conftest.read_bytes().replace(b"\n", b"\r\n"))
    assert verify_session(root, "crlf")["lock"]["status"] == "intact"


def test_locked_requirements_cannot_be_extended(tmp_path, capsys):
    root = _repo(tmp_path)
    _owner_locks(root, "late")
    assert _cli(root, "require", "--session", "late", "--id", "extra", "--scope", "artifact",
                "--description", "x", "--type", "file_exists", "--path", "calc.py") == 2
    assert "locked" in capsys.readouterr().err
    # An agent that appends the requirement record directly still meets the lock.
    record_event(root, "session.requirement", "late", requirement_id="weak", claim="weak",
                 scope="artifact", check={"type": "file_exists", "path": "calc.py"}, severity="RED")
    _claim_edit(root, "late", "calc.py", "def add")
    assert _cli(root, "finish", "--session", "late", "--status", "ok") == 2
    refused = _last_event(root, "late")
    assert refused["refuse_reason"] == "locked_checks_changed"
    assert refused["lock_check"]["findings"] == ["requirement declared after the lock: weak"]


def test_second_or_forged_lock_record_is_refused(tmp_path):
    root = _repo(tmp_path)
    _owner_locks(root, "relock")
    assert _cli(root, "lock", "--session", "relock") == 2
    record_event(root, "session.lock", "relock", lock_format="showwork-lock-v1",
                 requirement_ids=[], requirements_sha256="0" * 64, lock_patterns=[], locked_files={})
    assert verify_session(root, "relock")["lock"]["status"] == "invalid"


def test_lock_needs_requirements_and_comes_before_claims(tmp_path, capsys):
    root = _repo(tmp_path)
    assert _cli(root, "lock", "--session", "none") == 2
    assert _cli(root, "start", "--session", "none") == 0
    assert _cli(root, "lock", "--session", "none") == 2
    assert "declare acceptance requirements" in capsys.readouterr().err
    assert _cli(root, "start", "--session", "claimed") == 0
    assert _cli(root, "require", "--session", "claimed", "--id", "f", "--scope", "artifact",
                "--description", "f", "--type", "file_exists", "--path", "calc.py") == 0
    _claim_edit(root, "claimed", "calc.py", "def add")
    assert _cli(root, "lock", "--session", "claimed") == 2
    assert "before recording completion claims" in capsys.readouterr().err
    assert _cli(root, "start", "--session", "glob") == 0
    assert _cli(root, "require", "--session", "glob", "--id", "f", "--scope", "artifact",
                "--description", "f", "--type", "file_exists", "--path", "calc.py") == 0
    assert _cli(root, "lock", "--session", "glob", "--path", "nothing/**") == 2
    assert _cli(root, "lock", "--session", "glob", "--path", "../outside") == 2
    assert "matches no file" in capsys.readouterr().err


def test_gate_refuses_a_locked_check_changed_after_close(tmp_path):
    from showwork.outcomes import release_gate
    root = _repo(tmp_path)
    _owner_locks(root, "gated")
    _claim_edit(root, "gated", "calc.py", "def add")
    assert _cli(root, "finish", "--session", "gated", "--status", "ok") == 0
    assert release_gate(root, "gated")["verdict"] == "GREEN"
    (root / "scripts" / "run_tests.py").write_text("print('1 passed')\n", encoding="utf-8")
    result = release_gate(root, "gated")
    assert result["verdict"] == "RED"
    assert any("locked check file changed: scripts/run_tests.py" in e for e in result["errors"])


def test_readers_support_a_locked_receipt_and_badge_checks_the_lock(tmp_path):
    root = _repo(tmp_path)
    _owner_locks(root, "badge")
    _claim_edit(root, "badge", "calc.py", "def add")
    assert _cli(root, "finish", "--session", "badge", "--status", "ok") == 0
    reader = inspect_session(root, "badge")
    assert reader["spec_coverage"] == "supported_reading_fields"
    assert reader["recorded_outcome"] == "VERIFIED"
    (root / "scripts" / "run_tests.py").write_text("print('1 passed')\n", encoding="utf-8")
    badge = receipts_payload(root, session="badge")["records"][0]
    assert "locked check file changed: scripts/run_tests.py" in json.dumps(badge)
