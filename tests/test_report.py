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


def test_usage_report_and_fdr(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    start_session(tmp_path, "real-work", agent="codex")
    record_claim(tmp_path, "real-work", "a",
                 check={"type": "file_exists", "path": "a.txt"})
    assert finish_session(tmp_path, "real-work")[0] == 0

    start_session(tmp_path, "proof-campaign-r99", agent="codex",
                  note="research_proof")
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
