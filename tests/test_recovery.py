"""Real leaf checks exercise recovery; failed history never becomes success."""
import json
import subprocess

import pytest

from showwork.cli import main
from showwork.ledger import start_session, record_claim, finish_session, record_event, verify_session
from showwork.outcomes import record_requirement, release_gate, changed_sessions
from showwork.recovery import record_recovery, _work


def prepare(root):
    (root / "product.py").write_text("answer = 1\n")
    (root / "check.py").write_text(
        'from pathlib import Path\nassert "answer = 2" in Path("product.py").read_text()\nprint("verified")\n')
    start_session(root, "old")
    (root / "product.py").write_text("answer = 2\n")
    record_claim(root, "old", "product changed", {"type": "file_contains", "path": "product.py", "pattern": "answer"})
    assert finish_session(root, "old")[0] == 2
    assert finish_session(root, "old", status="blocked")[0] == 0
    start_session(root, "fresh")
    record_requirement(root, "fresh", "behavior", "product returns the updated answer", "behavior",
                       {"type": "command", "argv": ["python", "check.py"], "stdout_contains": "verified"})
    return {p: "behavior" for p in _work(root, "old")}


def recover(root, coverage=None):
    coverage = prepare(root) if coverage is None else coverage
    event = record_recovery(root, "fresh", "old", "requirements were omitted before claims", coverage)
    for p in coverage:
        record_claim(root, "fresh", f"freshly checked {p}", {"type": "file_exists", "path": p})
    return event


def test_recovery_keeps_failed_history_and_requires_fresh_execution(tmp_path):
    coverage = prepare(tmp_path)
    files = list((tmp_path / ".showwork").rglob("old.*"))
    before = {p: p.read_bytes() for p in files}
    recover(tmp_path, coverage)
    assert release_gate(tmp_path, "old")["verdict"] == "RED"  # no fresh close
    assert finish_session(tmp_path, "fresh")[0] == 0
    result = release_gate(tmp_path, "old")
    assert result["verdict"] == "GREEN"
    assert result["checks"]["outcome"]["verdict"] == "UNVERIFIED"
    assert result["original_errors"]
    assert verify_session(tmp_path, "old")["outcome"]["verdict"] == "UNVERIFIED"
    assert all(p.read_bytes() == raw for p, raw in before.items())
    (tmp_path / "product.py").write_text("answer = 3\n")
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


@pytest.mark.parametrize("coverage", [{}, {"product.py": "unknown"}, {"../escape": "behavior"}, {"./product.py": "behavior"}])
def test_missing_or_invalid_coverage_rejected(tmp_path, coverage):
    prepare(tmp_path)
    with pytest.raises(ValueError):
        record_recovery(tmp_path, "fresh", "old", "order error", coverage)


def test_coverage_includes_undeclared_changes_and_new_files(tmp_path):
    coverage = prepare(tmp_path)
    (tmp_path / "unclaimed.py").write_text("new work")
    with pytest.raises(ValueError, match="missing recovery coverage"):
        record_recovery(tmp_path, "fresh", "old", "order error", coverage)


def test_fresh_claims_cannot_omit_covered_paths(tmp_path):
    coverage = prepare(tmp_path)
    record_recovery(tmp_path, "fresh", "old", "order error", coverage)
    assert finish_session(tmp_path, "fresh")[0] == 2


def test_new_changes_after_recovery_are_not_hidden_by_fresh_snapshot(tmp_path):
    recover(tmp_path)
    (tmp_path / "later.py").write_text("uncovered")
    assert finish_session(tmp_path, "fresh")[0] == 2


@pytest.mark.parametrize("path", ["claims/old.jsonl", "sessions/old.jsonl", "snapshots/old.json"])
def test_altered_or_missing_old_evidence_fails(tmp_path, path):
    recover(tmp_path)
    assert finish_session(tmp_path, "fresh")[0] == 0
    (tmp_path / ".showwork" / path).unlink()
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


def test_appended_original_history_requires_new_review(tmp_path):
    recover(tmp_path)
    assert finish_session(tmp_path, "fresh")[0] == 0
    record_event(tmp_path, "observation", "old", note="new evidence")
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


@pytest.mark.parametrize("old", ["fresh", "missing", "../outside"])
def test_invalid_and_self_links_rejected(tmp_path, old):
    coverage = prepare(tmp_path)
    with pytest.raises(ValueError):
        record_recovery(tmp_path, "fresh", old, "order error", coverage)


def test_existing_acceptance_requirements_cannot_be_weakened(tmp_path):
    coverage = prepare(tmp_path)
    record_event(tmp_path, "session.requirement", "old", requirement_id="retained", scope="artifact",
                 check={"type": "file_exists", "path": "missing.txt"})
    with pytest.raises(ValueError, match="existing requirements"):
        record_recovery(tmp_path, "fresh", "old", "order error", coverage)


def test_no_artifact_only_or_late_recovery(tmp_path):
    coverage = prepare(tmp_path)
    record_claim(tmp_path, "fresh", "premature", {"type": "file_exists", "path": "product.py"})
    with pytest.raises(ValueError, match="before completion claims"):
        record_recovery(tmp_path, "fresh", "old", "order error", coverage)


def test_unverified_requirement_blocks_both_sessions(tmp_path):
    recover(tmp_path)
    (tmp_path / "product.py").write_text("answer = 0\n")
    assert finish_session(tmp_path, "fresh")[0] == 2
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


def test_ambiguous_and_cyclic_links_fail_closed(tmp_path):
    event = recover(tmp_path)
    assert finish_session(tmp_path, "fresh")[0] == 0
    record_event(tmp_path, "session.recovery", "other", **{k: v for k, v in event.items() if k not in {"session", "ts", "event", "prev", "hash"}})
    assert release_gate(tmp_path, "old")["verdict"] == "RED"
    record_event(tmp_path, "session.recovery", "old", supersedes="fresh", reason="cycle", coverage={})
    assert release_gate(tmp_path, "fresh")["verdict"] == "RED"


def test_changed_since_gates_both_committed_receipts(tmp_path, capsys):
    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True, check=True).stdout.strip()
    git("init")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Recovery test")
    (tmp_path / "base.txt").write_text("base")
    git("add", ".")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")
    recover(tmp_path)
    assert finish_session(tmp_path, "fresh")[0] == 0
    assert release_gate(tmp_path, "old", require_tracked=True)["verdict"] == "RED"
    git("add", ".")
    git("commit", "-m", "both receipts")
    assert changed_sessions(tmp_path, base) == ["fresh", "old"]
    assert main(["--root", str(tmp_path), "gate", "--changed-since", base, "--require-tracked"]) == 0
    assert "original outcome remains UNVERIFIED" in capsys.readouterr().out


def test_cli_records_coverage_then_still_requires_verified_close(tmp_path):
    coverage = prepare(tmp_path)
    path = tmp_path / ".showwork/coverage.json"
    path.write_text(json.dumps(coverage))
    assert main(["--root", str(tmp_path), "recover", "--session", "fresh", "--supersedes", "old",
                 "--reason", "order error", "--coverage-file", ".showwork/coverage.json"]) == 0
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


def test_artifact_only_replacement_rejected(tmp_path):
    coverage = prepare(tmp_path)
    start_session(tmp_path, "artifact-only")
    record_requirement(tmp_path, "artifact-only", "artifact", "file exists", "artifact",
                       {"type": "file_exists", "path": "product.py"})
    with pytest.raises(ValueError, match="executable"):
        record_recovery(tmp_path, "artifact-only", "old", "order error", coverage)


@pytest.mark.parametrize("change", ["requirements", "reopen", "mutate", "ambiguous"])
def test_changed_replacement_invalidates_recovery(tmp_path, change):
    recover(tmp_path)
    assert finish_session(tmp_path, "fresh")[0] == 0
    if change == "requirements":
        record_event(tmp_path, "session.requirement", "fresh", requirement_id="late", scope="artifact",
                     check={"type": "file_exists", "path": "product.py"})
    elif change == "reopen":
        start_session(tmp_path, "fresh")
    elif change == "mutate":
        # Product still passes the leaf assertion, but differs from the closed outcome.
        (tmp_path / "product.py").write_text("answer = 2\nextra = 1\n")
    else:
        record_event(tmp_path, "session.recovery", "fresh", supersedes="old", coverage={})
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


@pytest.mark.parametrize("coverage", [[], {"../../secret": "behavior"}, {"product.py": []}])
def test_malformed_recovery_event_is_red_not_a_crash(tmp_path, coverage):
    prepare(tmp_path)
    record_event(tmp_path, "session.recovery", "fresh", supersedes="old", coverage=coverage)
    assert finish_session(tmp_path, "fresh")[0] == 2
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


def test_original_artifact_hash_and_chain_corruption_are_not_excused(tmp_path):
    coverage = prepare(tmp_path)
    artifact = tmp_path / ".showwork/artifacts/old/evidence.bin"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"\x00evidence\r\n")
    recover(tmp_path, coverage)
    assert finish_session(tmp_path, "fresh")[0] == 0
    artifact.write_bytes(b"\x00evidence\n")
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


def test_old_chain_corruption_is_not_excused(tmp_path):
    recover(tmp_path)
    assert finish_session(tmp_path, "fresh")[0] == 0
    path = tmp_path / ".showwork/claims/old.jsonl"
    path.write_bytes(path.read_bytes().replace(b"product changed", b"product forged"))
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


def test_disabled_commands_cannot_certify_recovery(tmp_path, monkeypatch):
    recover(tmp_path)
    assert finish_session(tmp_path, "fresh")[0] == 0
    monkeypatch.setenv("SHOWWORK_NO_COMMANDS", "1")
    assert release_gate(tmp_path, "old")["verdict"] == "RED"


def test_unrelated_tampering_still_blocks_recovered_release(tmp_path):
    recover(tmp_path)
    assert finish_session(tmp_path, "fresh")[0] == 0
    path = tmp_path / ".showwork/claims-2020-01-01.jsonl"
    path.write_text('{"session":"other","claim":"tampered","prev":"' + 'f' * 64 + '"}\n')
    assert release_gate(tmp_path, "old")["verdict"] == "RED"
