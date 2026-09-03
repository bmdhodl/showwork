"""Operator report + status helpers."""

from showwork.ledger import finish_session, record_claim, start_session
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
