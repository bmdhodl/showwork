"""REGRESSION: matching strings must not certify GolfFly's behavior."""

import json
import subprocess
import os
import sys
from pathlib import Path

import pytest

from showwork.cli import main
from showwork.ledger import finish_session, record_claim, start_session, verify_session


def cli(root, *args):
    return main(["--root", str(root), *args])


def require(root, name="shot", check=None, scope="behavior"):
    check = check or {"type": "command", "argv": ["python", "check.py"]}
    return cli(root, "require", "--session", "golf", "--id", name,
               "--description", "The controller preserves the model's shot",
               "--scope", scope, "--check-json", json.dumps(check))


def test_golffly_magic_strings_cannot_close_an_outcome(tmp_path, capsys):
    (tmp_path / "connectome.js").write_text('// m.weights\nreturn "hard-coded";')
    (tmp_path / "receipt.json").write_text('{"invented_count":2360}')
    start_session(tmp_path, "golf")
    for path, pattern, claim in [
        ("connectome.js", "m.weights", "GolfFly decisions use a measured graph"),
        ("receipt.json", "2360", "2360 tests passed and HDR is verified"),
    ]:
        record_claim(tmp_path, "golf", claim,
                     {"type": "file_contains", "path": path, "pattern": pattern})
    assert cli(tmp_path, "verify", "--session", "golf", "--no-report") == 0
    assert "Outcome: UNVERIFIED" in capsys.readouterr().out
    code, state = finish_session(tmp_path, "golf")
    assert code == 2
    assert state["outcome"]["verdict"] == "UNVERIFIED"


def test_behavior_requirement_rejects_string_check(tmp_path):
    start_session(tmp_path, "golf")
    assert require(tmp_path, check={"type": "file_contains", "path": "receipt.json",
                                    "pattern": "2360"}) == 2


def test_actual_controller_failure_then_repair(tmp_path):
    (tmp_path / "controller.py").write_text('def shot(model): return 10\n')
    (tmp_path / "check.py").write_text(
        'from controller import shot\nassert shot(3) == 3\nprint("shot preserved")\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    record_claim(tmp_path, "golf", "controller.py exists",
                 {"type": "file_exists", "path": "controller.py"})
    assert finish_session(tmp_path, "golf")[0] == 2
    (tmp_path / "controller.py").write_text('def shot(model): return model\n')
    code, state = finish_session(tmp_path, "golf")
    assert code == 0
    assert state["outcome"]["verdict"] == "VERIFIED"
    result = next(r for r in state["results"] if r.get("requirement_id") == "shot")
    assert result["evidence"]["exit_code"] == 0
    assert len(result["evidence"]["stdout_sha256"]) == 64
    assert len(result["evidence"]["script_sha256"]) == 64


def test_requirements_cannot_be_weakened_or_retracted_as_claims(tmp_path):
    (tmp_path / "check.py").write_text('raise SystemExit(1)\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    assert require(tmp_path, check={"type": "file_exists", "path": "check.py"},
                   scope="artifact") == 2
    cli(tmp_path, "retract", "--session", "golf", "--claim",
        "The controller preserves the model's shot", "--reason", "skip the test")
    assert finish_session(tmp_path, "golf")[0] == 2


def test_checks_only_close_is_explicit_and_not_an_outcome(tmp_path):
    (tmp_path / "file.txt").write_text("present")
    start_session(tmp_path, "golf")
    record_claim(tmp_path, "golf", "file exists",
                 {"type": "file_exists", "path": "file.txt"})
    assert cli(tmp_path, "finish", "--session", "golf", "--checks-only") == 0
    state = verify_session(tmp_path, "golf")
    assert state["outcome"]["verdict"] == "UNVERIFIED"
    assert cli(tmp_path, "gate", "--session", "golf") == 2


def test_empty_session_cannot_pass_release_gate(tmp_path):
    assert cli(tmp_path, "gate", "--session", "missing") == 2


def test_read_only_badge_does_not_certify_a_prose_claim(tmp_path):
    from showwork.receipts import evidence_for_session
    (tmp_path / "file.txt").write_text("2360")
    start_session(tmp_path, "golf")
    record_claim(tmp_path, "golf", "All tests and HDR passed",
                 {"type": "file_contains", "path": "file.txt", "pattern": "2360"})
    badge = evidence_for_session(tmp_path, "golf")
    assert badge["state"] == "claimed"
    assert badge["claim"] == "All tests and HDR passed"
    assert "2360" in badge["detail"]


def test_gate_detects_missing_claim_file_in_fresh_checkout(tmp_path):
    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True,
                              text=True, check=True)
    git("init")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Receipt test")
    (tmp_path / "check.py").write_text('print("passed")\n')
    git("add", "check.py")
    git("commit", "-m", "fixture")
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    record_claim(tmp_path, "golf", "check.py exists",
                 {"type": "file_exists", "path": "check.py"})
    assert finish_session(tmp_path, "golf")[0] == 0
    assert cli(tmp_path, "gate", "--session", "golf", "--require-tracked") == 2
    git("add", ".showwork")
    git("commit", "-m", "receipt")
    assert cli(tmp_path, "gate", "--session", "golf", "--require-tracked") == 0
    (tmp_path / ".showwork/claims/golf.jsonl").unlink()
    assert cli(tmp_path, "gate", "--session", "golf") == 2


def test_one_pass_cannot_hide_an_unmet_requirement(tmp_path):
    (tmp_path / "check.py").write_text('print("passed")\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    assert require(tmp_path, "video", {"type": "file_exists", "path": "video.mp4"}, "artifact") == 0
    code, state = finish_session(tmp_path, "golf")
    assert code == 2
    assert state["outcome"]["passed"] == 1
    assert state["outcome"]["total"] == 2


def test_disabled_command_never_certifies_behavior(tmp_path, monkeypatch):
    (tmp_path / "check.py").write_text('print("passed")\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    monkeypatch.setenv("SHOWWORK_NO_COMMANDS", "1")
    assert finish_session(tmp_path, "golf")[0] == 2
    assert verify_session(tmp_path, "golf")["outcome"]["verdict"] == "UNVERIFIED"


def test_read_only_requirement_does_not_run_python(tmp_path):
    from showwork.receipts import evidence_for_session
    (tmp_path / "check.py").write_text('from pathlib import Path\nPath("executed").touch()\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    assert evidence_for_session(tmp_path, "golf")["state"] == "unknown"
    assert not (tmp_path / "executed").exists()


def test_acceptance_command_changing_source_fails(tmp_path):
    (tmp_path / "controller.py").write_text("original")
    (tmp_path / "check.py").write_text(
        'from pathlib import Path\nPath("controller.py").write_text("changed")\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    code, state = finish_session(tmp_path, "golf")
    assert code == 2
    assert any("source tree changed" in r["detail"] for r in state["results"])


def test_gate_refuses_reopened_session(tmp_path):
    (tmp_path / "check.py").write_text('print("passed")\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    assert finish_session(tmp_path, "golf")[0] == 0
    start_session(tmp_path, "golf")
    assert cli(tmp_path, "gate", "--session", "golf") == 2


def test_cli_subprocess_demo_exercises_real_controller(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    result = subprocess.run([sys.executable, str(root / "examples/evidence_scope_demo.py")],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("Close refused") == 2
    assert "Close accepted" in result.stdout


def test_wrapper_cannot_promote_string_check_to_outcome(tmp_path):
    (tmp_path / "proof.txt").write_text("2360")
    start_session(tmp_path, "golf")
    record_claim(tmp_path, "golf", "All tests passed",
                 {"type": "file_contains", "path": "proof.txt", "pattern": "2360"})
    assert cli(tmp_path, "run", "--session", "golf", "--gate", "--",
               sys.executable, "-c", "print('done')") == 2


def test_doctor_reports_actual_import_and_metadata_mismatch(monkeypatch, tmp_path, capsys):
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.0.0")
    assert cli(tmp_path, "doctor", "--json") == 2
    identity = json.loads(capsys.readouterr().out)
    assert identity["consistent"] is False
    assert identity["module"].endswith("outcomes.py")


def test_windows_receipt_verifies_after_git_lf_checkout(tmp_path):
    # REGRESSION: fresh Linux CI called every untouched CRLF source file changed.
    source = tmp_path / "unchanged.py"
    source.write_bytes(b"value = 1\r\n")
    start_session(tmp_path, "golf")
    source.write_bytes(b"value = 1\n")
    assert verify_session(tmp_path, "golf")["verdict"] == "GREEN"
    source.write_bytes(b"value = 2\n")
    assert verify_session(tmp_path, "golf")["verdict"] == "RED"


def test_binary_line_endings_still_count_as_changed(tmp_path):
    source = tmp_path / "data.bin"
    source.write_bytes(b"\x00\xff\r\n")
    start_session(tmp_path, "golf")
    source.write_bytes(b"\x00\xff\n")
    assert verify_session(tmp_path, "golf")["verdict"] == "RED"


def test_deleted_entire_receipt_remains_in_changed_session_gate(tmp_path):
    from showwork.outcomes import changed_sessions
    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True,
                              text=True, check=True).stdout.strip()
    git("init")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Receipt test")
    start_session(tmp_path, "removed")
    git("add", ".showwork")
    git("commit", "-m", "receipt")
    base = git("rev-parse", "HEAD")
    for path in (tmp_path / ".showwork").rglob("*"):
        if path.is_file():
            path.unlink()
    start_session(tmp_path, "replacement")
    git("add", "-A")
    git("commit", "-m", "replace receipts")
    assert changed_sessions(tmp_path, base) == ["removed", "replacement"]


def test_unrelated_pre_chain_history_is_visible_without_certifying_it(tmp_path):
    from showwork.outcomes import release_gate
    (tmp_path / "check.py").write_text('print("passed")\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    assert finish_session(tmp_path, "golf")[0] == 0
    (tmp_path / ".showwork/claims-2020-01-01.jsonl").write_text(
        '{"session":"historical","claim":"old unanchored observation"}\n')
    result = release_gate(tmp_path, "golf")
    assert result["verdict"] == "GREEN"
    assert result["historical_integrity"] == "YELLOW"
    assert result["integrity_scope"] == "selected session; unrelated RED findings still fail"


def test_unrelated_tampering_still_fails_release_gate(tmp_path):
    from showwork.outcomes import release_gate
    (tmp_path / "check.py").write_text('print("passed")\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    assert finish_session(tmp_path, "golf")[0] == 0
    path = tmp_path / ".showwork/claims-2020-01-01.jsonl"
    path.write_text('{"session":"other","claim":"tampered","prev":"' + 'f'*64 + '"}\n')
    assert release_gate(tmp_path, "golf")["verdict"] == "RED"


def test_moved_receipt_cannot_hide_deleted_session(tmp_path):
    # REGRESSION: Git rename detection hid the deleted source receipt path.
    from showwork.outcomes import changed_sessions
    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True,
                              text=True, check=True).stdout.strip()
    git("init")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Receipt test")
    git("config", "diff.renames", "true")
    start_session(tmp_path, "removed")
    git("add", ".showwork")
    git("commit", "-m", "receipt")
    base = git("rev-parse", "HEAD")
    paths = list((tmp_path / ".showwork").rglob("*"))
    (tmp_path / ".showwork/archive").mkdir()
    for path in paths:
        if path.is_file():
            path.rename(tmp_path / ".showwork/archive" / path.name)
    start_session(tmp_path, "replacement")
    git("add", "-A")
    git("commit", "-m", "archive receipts")
    assert changed_sessions(tmp_path, base) == ["removed", "replacement"]


def test_gated_wrapper_persists_command_evidence(tmp_path):
    # REGRESSION: wrapper closes dropped evidence that ordinary finish saved.
    from showwork.ledger import load_all_events
    (tmp_path / "check.py").write_text('print("passed")\n')
    start_session(tmp_path, "golf")
    assert require(tmp_path) == 0
    assert cli(tmp_path, "run", "--session", "golf", "--gate", "--",
               sys.executable, "-c", "print('done')") == 0
    close = [e for e in load_all_events(tmp_path) if e["event"] == "session.finish"][-1]
    assert close["command_evidence"][0]["evidence"]["exit_code"] == 0
    assert close["command_evidence"][0]["requirement_id"] == "shot"


def test_claim_cannot_impersonate_acceptance_requirement(tmp_path):
    # REGRESSION: author-supplied requirement_id was trusted in ordinary claims.
    from showwork.ledger import _append, session_claims_path
    (tmp_path / "fake.txt").write_text("2360")
    start_session(tmp_path, "golf")
    _append(session_claims_path(tmp_path, "golf"), {
        "session": "golf", "claim": "All tests passed", "requirement_id": "forged",
        "scope": "behavior", "verification_scope": "declared acceptance check",
        "check": {"type": "file_contains", "path": "fake.txt", "pattern": "2360"},
    })
    state = verify_session(tmp_path, "golf")
    assert state["outcome"]["verdict"] == "UNVERIFIED"
    assert state["outcome"]["total"] == 0
    assert finish_session(tmp_path, "golf")[0] == 2


def test_worktree_git_pointer_is_not_application_source(tmp_path):
    # REGRESSION: a worktree .git file became a deletion in a regular CI clone.
    from showwork.snapshot import capture_tree, undeclared_results
    (tmp_path / ".git").write_text("gitdir: /private/worktree/pointer\n")
    assert ".git" not in capture_tree(tmp_path)
    # Existing snapshots keep their bytes and hash; metadata is ignored at read.
    from showwork.snapshot import _files_digest
    import hashlib
    files = {".git": hashlib.sha256((tmp_path / ".git").read_bytes()).hexdigest()}
    meta = {"sha256": _files_digest(files), "count": 1}
    snap = tmp_path / ".showwork/snapshots/old.json"
    snap.parent.mkdir(parents=True)
    snap.write_text(json.dumps({**meta, "files": files}))
    (tmp_path / ".git").unlink()
    (tmp_path / ".git").mkdir()
    assert undeclared_results(tmp_path, [], {"tree_snapshot": meta}, snap) == []


@pytest.mark.parametrize("local_name", [".env.local", "install.log"])
def test_machine_local_inputs_do_not_break_portable_receipts(tmp_path, local_name):
    from showwork.snapshot import capture_tree
    (tmp_path / local_name).write_text("local-only data")
    (tmp_path / ".env.example").write_text("public template")
    captured = capture_tree(tmp_path)
    assert local_name not in captured
    assert ".env.example" in captured
