"""Operator report + status helpers."""

import json

from showwork.ledger import (
    finish_session,
    record_claim,
    record_event,
    session_events_path,
    start_session,
)
from showwork.report import analyze_fdr, session_status, usage_report
from showwork.outcomes import record_requirement


def test_unscoped_status_reads_each_claim_file_once(tmp_path, monkeypatch):
    """REGRESSION: adding sessions must not multiply claim-file reads."""
    import showwork.ledger as ledger

    (tmp_path / "present.txt").write_text("yes", encoding="utf-8")
    for index in range(8):
        name = f"read-count-{index}"
        start_session(tmp_path, name)
        record_claim(tmp_path, name, "exists",
                     check={"type": "file_exists", "path": "present.txt"})
    reads = {}
    original = ledger._read_jsonl

    def counted(path):
        if path.parent.name == "claims":
            reads[path] = reads.get(path, 0) + 1
        return original(path)

    monkeypatch.setattr(ledger, "_read_jsonl", counted)
    status = session_status(tmp_path)
    assert len(status["sessions"]) == 8
    assert all(row["live_verdict"] == "GREEN" for row in status["sessions"])
    assert len(reads) == 8 and max(reads.values()) == 1, reads


def test_status_snapshot_preserves_session_selection_and_refreshes(tmp_path, monkeypatch):
    """Mixed/split files, stem collisions and malformed rows retain their meaning."""
    import showwork.ledger as ledger
    import showwork.report as report

    (tmp_path / "present.txt").write_text("yes", encoding="utf-8")
    names = ["target", "other", "parse-only", "empty", "collision", "ambiguous", "single"]
    for name in names:
        start_session(tmp_path, name)
    folder = tmp_path / ".showwork" / "claims"
    folder.mkdir(exist_ok=True)

    def claim(session, text, ts="2026-10-02T00:00:00"):
        return {"session": session, "claim": text, "ts": ts,
                "check": {"type": "file_exists", "path": "present.txt"}}

    def write(path, records, malformed=False):
        path.write_text("".join(json.dumps(row) + "\n" for row in records)
                        + ("{broken\n" if malformed else ""), encoding="utf-8")

    old = claim("target", "repeat")
    write(tmp_path / ".showwork" / "claims-2026-10-02.jsonl", [old, claim("other", "shared"),
          {"session": "other", "retracts": {"session": "target", "claim": "repeat"},
           "retracted": True, "ts": "2026-10-02T00:00:01"}], malformed=True)
    # The current stream stays last even after the clock rolls back.
    write(folder / "target.jsonl", [claim("target", "repeat", "2026-10-01T00:00:00")])
    write(folder / "parse-only.jsonl", [], malformed=True)
    write(folder / "empty.jsonl", [])
    write(folder / "collision.jsonl", [claim("other", "collision owner")])
    write(folder / "old-a.jsonl", [claim("ambiguous", "a")])
    write(folder / "old-b.jsonl", [claim("ambiguous", "b")])
    write(folder / "old-single.jsonl", [claim("single", "one leftover")])
    write(folder / "other.jsonl", [{"session": "other", "supersedes": {
        "session": "target", "claim": "repeat", "ts": old["ts"]},
        "supersession_reason": "replaced", "ts": "2026-10-03T00:00:00"}])

    snapshot = ledger._snapshot_claim_files(tmp_path)
    for name in names:
        assert ledger.claims_for_session(tmp_path, name, claim_files=snapshot) == ledger.claims_for_session(tmp_path, name)
    cached = session_status(tmp_path)
    with monkeypatch.context() as context:
        context.setattr(report, "_snapshot_claim_files", lambda root: None)
        assert session_status(tmp_path) == cached
    write(folder / "single.jsonl", [claim("single", "new append")])
    refreshed = session_status(tmp_path)
    assert refreshed != cached
    assert next(row for row in refreshed["sessions"] if row["session"] == "single")["live_total"] == 2


def test_status_snapshot_keeps_linked_claims_directory_fallback_last(tmp_path):
    """REGRESSION: an in-ledger directory alias must retain leftover-stem order."""
    import os
    import subprocess
    from showwork.ledger import _snapshot_claim_files, claims_for_session

    ledger = tmp_path / ".showwork"
    actual = ledger / "claim-storage"
    actual.mkdir(parents=True)
    link = ledger / "claims"
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(actual)],
                       check=True, capture_output=True)
    else:
        link.symlink_to(actual, target_is_directory=True)
    (ledger / "sessions.jsonl").write_text(json.dumps({
        "event": "session.start", "session": "linked", "ts": "2026-10-01T00:00:00"
    }) + "\n", encoding="utf-8")
    (actual / "old-stem.jsonl").write_text(json.dumps({
        "session": "linked", "claim": "missing", "ts": "2026-10-01T00:00:00",
        "check": {"type": "file_exists", "path": "missing.txt"}
    }) + "\n", encoding="utf-8")
    (ledger / "claims-2026-10-02.jsonl").write_text(json.dumps({
        "session": "linked", "ts": "2026-10-02T00:00:00",
        "retracts": {"session": "linked", "claim": "missing"},
        "retracted": True, "retraction_reason": "old observation"
    }) + "\n", encoding="utf-8")
    expected = claims_for_session(tmp_path, "linked")
    assert expected[-1]["claim"] == "missing"
    assert claims_for_session(tmp_path, "linked", claim_files=_snapshot_claim_files(tmp_path)) == expected
    assert session_status(tmp_path)["sessions"][0]["live_verdict"] == "RED"


def test_usage_report_and_fdr(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    start_session(tmp_path, "real-work", agent="codex")
    record_requirement(tmp_path, "real-work", "file", "a.txt exists", "artifact",
                       {"type": "file_exists", "path": "a.txt"})
    record_claim(tmp_path, "real-work", "a",
                 check={"type": "file_exists", "path": "a.txt"})
    assert finish_session(tmp_path, "real-work")[0] == 0

    start_session(tmp_path, "proof-campaign-r99", agent="codex",
                  note="research_proof")
    record_requirement(tmp_path, "proof-campaign-r99", "file", "a.txt exists", "artifact",
                       {"type": "file_exists", "path": "a.txt"})
    record_claim(tmp_path, "proof-campaign-r99", "a",
                 check={"type": "file_exists", "path": "a.txt"})
    assert finish_session(tmp_path, "proof-campaign-r99")[0] == 0

    full = usage_report(tmp_path)
    assert full["session_starts"] == 2
    assert full["check_types"]["file_exists"] == 2
    assert full["fdr"]["eligible_sessions"] == 2

    trimmed = usage_report(tmp_path, exclude_campaign=True)
    assert trimmed["fdr"]["eligible_sessions"] == 1
    assert "real-work" in analyze_fdr(tmp_path, exclude_campaign=True)["sessions"]
    assert "proof-campaign-r99" not in analyze_fdr(
        tmp_path, exclude_campaign=True
    )["sessions"]


def test_session_status_open_vs_closed(tmp_path):
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    start_session(tmp_path, "open-s")
    record_requirement(tmp_path, "open-s", "file", "b.txt exists", "artifact",
                       {"type": "file_exists", "path": "b.txt"})
    record_claim(tmp_path, "open-s", "b",
                 check={"type": "file_exists", "path": "b.txt"})
    status = session_status(tmp_path, session="open-s")
    assert status["sessions"][0]["open"] is True
    assert status["sessions"][0]["live_verdict"] == "GREEN"
    finish_session(tmp_path, "open-s")
    status = session_status(tmp_path, session="open-s")
    assert status["sessions"][0]["open"] is False
    start_session(tmp_path, "open-s")
    status = session_status(tmp_path, session="open-s")
    assert status["sessions"][0]["open"] is True


def test_session_status_uses_latest_close_attempt(tmp_path):
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    start_session(tmp_path, "s")
    record_requirement(tmp_path, "s", "file", "b.txt exists", "artifact",
                       {"type": "file_exists", "path": "b.txt"})
    record_claim(tmp_path, "s", "b",
                 check={"type": "file_exists", "path": "b.txt"})
    assert finish_session(tmp_path, "s")[0] == 0
    start_session(tmp_path, "s")
    record_claim(tmp_path, "s", "missing",
                 check={"type": "file_exists", "path": "missing.txt"})
    assert finish_session(tmp_path, "s")[0] == 2
    status = session_status(tmp_path, session="s")
    assert status["sessions"][0]["last_claims_verdict"] == "RED"


def test_split_event_files_keep_later_start_open(tmp_path):
    events_dir = tmp_path / ".showwork" / "sessions"
    events_dir.mkdir(parents=True)
    old = events_dir / "z-legacy.jsonl"
    old.write_text(
        json.dumps({"event": "session.start", "session": "split-e",
                    "ts": "2026-09-02T20:00:00"}) + "\n"
        + json.dumps({"event": "session.finish", "session": "split-e",
                      "ts": "2026-09-02T20:01:00", "status": "ok"}) + "\n",
        encoding="utf-8",
    )
    record_event(tmp_path, "session.start", "split-e", agent="cursor")
    assert session_events_path(tmp_path, "split-e") == old.resolve()
    assert not (events_dir / "split-e.jsonl").exists()
    status = session_status(tmp_path, session="split-e")
    assert status["sessions"][0]["open"] is True


def test_legacy_sessions_file_stays_before_per_session_events(tmp_path):
    ledger = tmp_path / ".showwork"
    ledger.mkdir()
    (ledger / "sessions.jsonl").write_text(
        json.dumps({"event": "session.start", "session": "s",
                    "ts": "2026-09-02T20:00:00"}) + "\n"
        + json.dumps({"event": "session.finish", "session": "s",
                      "ts": "2026-09-02T20:01:00", "status": "ok"}) + "\n",
        encoding="utf-8",
    )
    (ledger / "sessions").mkdir()
    (ledger / "sessions" / "s.jsonl").write_text(
        json.dumps({"event": "session.start", "session": "s",
                    "ts": "2026-09-02T19:00:00"}) + "\n",
        encoding="utf-8",
    )
    status = session_status(tmp_path, session="s")
    assert status["sessions"][0]["open"] is True
