"""Stop-hook adapter tests: observe every verdict, gate none of them."""

import io
import json
import sys

from showwork.cli import main
from showwork.ledger import record_claim, sessions_path


def _events(root):
    return [json.loads(line) for line in
            sessions_path(root).read_text(encoding="utf-8").splitlines()]


def test_stop_hook_records_green_verdict(tmp_path, monkeypatch, capsys):
    (tmp_path / "proof.txt").write_text("real", encoding="utf-8")
    record_claim(tmp_path, "hook-green", "proof exists",
                 check={"type": "file_exists", "path": "proof.txt"})
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "session_id": "hook-green", "cwd": str(tmp_path),
        "hook_event_name": "Stop",
    })))

    assert main(["--root", str(tmp_path), "stop-hook"]) == 0
    event = _events(tmp_path)[-1]
    assert event["event"] == "session.finish"
    assert event["session"] == "hook-green"
    assert event["observed_by"] == "stop-hook"
    assert event["claims_verdict"] == "GREEN"
    assert event["claims_unverified"] == []
    assert "stop observed: GREEN" in capsys.readouterr().out


def test_stop_hook_records_red_but_exits_zero(tmp_path, monkeypatch):
    record_claim(tmp_path, "hook-red", "missing proof exists",
                 check={"type": "file_exists", "path": "missing.txt"})
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"sessionId":"hook-red"}'))

    assert main(["--root", str(tmp_path), "stop-hook"]) == 0
    event = _events(tmp_path)[-1]
    assert event["claims_verdict"] == "RED"
    assert event["claims_unverified"][0]["claim"] == "missing proof exists"


def test_stop_hook_malformed_payload_never_breaks_shutdown(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-json"))
    assert main(["--root", str(tmp_path), "stop-hook"]) == 0
    assert "showwork stop-hook" in capsys.readouterr().err
