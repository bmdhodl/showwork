"""Reader capabilities and history do not grant execution authority."""

import json
import subprocess
from pathlib import Path
import pytest

from showwork.ledger import record_claim, start_session
from showwork.receipts import evidence_for_session, receipts_payload
from showwork.reader import inspect_session

FIXTURES = Path(__file__).parent / "fixtures" / "readers"
EXPECTED = json.loads((FIXTURES / "expected.json").read_text())


@pytest.mark.parametrize("name", EXPECTED)
def test_frozen_reader_labels(name, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("reader started a subprocess")))
    result = inspect_session(FIXTURES / name, "fixture")
    assert {key: result[key] for key in EXPECTED[name]} == EXPECTED[name]


def test_closed_reopened_and_missing_manifest_are_distinct():
    closed = inspect_session(FIXTURES / "closed", "fixture")
    assert closed["manifest"] == "matches"
    assert closed["freshness"] == "recorded_close"
    assert inspect_session(FIXTURES / "reopened", "fixture")["freshness"] == "reopened"
    assert inspect_session(FIXTURES / "missing-manifest", "fixture")["manifest"] == "absent"
    assert inspect_session(FIXTURES / "changed-claims", "fixture")["manifest"] == "mismatch"


def test_symlink_escape_is_unknown(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    try:
        (workspace / ".showwork").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("host does not permit symlink creation")
    assert inspect_session(workspace, "fixture")["integrity"] == "unknown"
    assert evidence_for_session(workspace, "fixture")["state"] == "unknown"


def test_oversized_receipt_is_unknown(tmp_path, monkeypatch):
    from showwork import reader
    base = tmp_path / ".showwork" / "sessions"
    base.mkdir(parents=True)
    (base / "fixture.jsonl").write_text("x" * 64)
    monkeypatch.setattr(reader, "MAX_FILE_BYTES", 32)
    assert inspect_session(tmp_path, "fixture")["integrity"] == "unknown"


def test_receipt_view_never_starts_git_or_regex_workers(tmp_path, monkeypatch):
    """REGRESSION: opening a receipt started Git and Python regex workers."""
    (tmp_path / "ok.txt").write_text("ok")
    start_session(tmp_path, "reader")
    record_claim(tmp_path, "reader", "text", {
        "type": "file_contains", "path": "ok.txt", "pattern": "ok",
    })
    (tmp_path / ".git").mkdir()
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(args)
        raise AssertionError("reader attempted a subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)
    result = evidence_for_session(tmp_path, "reader")
    receipts_payload(tmp_path, session="reader")
    assert calls == []
    assert result["state"] == "unknown"
    assert result["capabilities"]["processes"] is False


def test_cli_receipts_root_resolution_is_process_free(tmp_path, monkeypatch, capsys):
    from showwork.cli import main
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("receipt CLI launched Git")))
    assert main(["--root", str(tmp_path), "receipts", "--session", "empty", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["empty"] is True


def test_clock_rollback_cannot_hide_a_reopened_session(tmp_path, monkeypatch):
    """REGRESSION: timestamp sorting moved a newly appended start before finish."""
    import shutil
    from showwork.ledger import record_event
    shutil.copytree(FIXTURES / "closed" / ".showwork", tmp_path / ".showwork")
    assert inspect_session(tmp_path, "fixture")["recorded_outcome"] == "VERIFIED"
    monkeypatch.setattr("showwork.ledger._now", lambda: "2000-01-01T00:00:00Z")
    record_event(tmp_path, "session.start", "fixture")
    result = inspect_session(tmp_path, "fixture")
    assert result["freshness"] == "reopened"
    assert result["recorded_outcome"] == "UNVERIFIED"


def test_split_claim_stream_current_path_follows_old_retraction(tmp_path, monkeypatch):
    """REGRESSION: filename order made an older retraction cancel a newer claim."""
    from showwork.ledger import _append, record_retraction, finish_session
    from showwork.outcomes import record_requirement
    from showwork.reader import load_receipt
    (tmp_path / "anchor.txt").write_text("real")
    start_session(tmp_path, "task")
    (tmp_path / "artifact.txt").write_text("real")
    check = {"type": "file_exists", "path": "artifact.txt"}
    record_requirement(tmp_path, "task", "file", "anchor exists", "artifact",
                       {"type": "file_exists", "path": "anchor.txt"})
    record_claim(tmp_path, "task", "artifact", check)
    record_retraction(tmp_path, "task", "artifact", "replaced")
    current = tmp_path / ".showwork" / "claims" / "task.jsonl"
    old = current.with_name("z-old.jsonl")
    # Copying bytes would break the per-filename genesis. Build the remapped
    # stream with the normal chained writer instead.
    rows = [json.loads(line) for line in current.read_text().splitlines()]
    for row in rows:
        _append(old, row)
    monkeypatch.setattr("showwork.ledger._now", lambda: "2000-01-01T00:00:00Z")
    record_claim(tmp_path, "task", "artifact", check)
    exit_code, _state = finish_session(tmp_path, "task", "ok")
    assert exit_code == 0
    assert load_receipt(tmp_path, "task")["claims"][-1].get("retracted") is not True
    assert evidence_for_session(tmp_path, "task")["state"] == "verified"
    (tmp_path / "artifact.txt").unlink()
    assert evidence_for_session(tmp_path, "task")["state"] == "failed"
