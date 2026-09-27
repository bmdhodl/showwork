"""Stop-hook adapter tests: observe every verdict, gate none of them."""

import io
import json
import sys

from showwork.cli import main
from showwork.ledger import record_claim, sessions_path


def _events(root, session):
    return [json.loads(line) for line in
            sessions_path(root, session).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def test_stop_hook_records_green_verdict(tmp_path, monkeypatch, capsys):
    (tmp_path / "proof.txt").write_text("real", encoding="utf-8")
    record_claim(tmp_path, "hook-green", "proof exists",
                 check={"type": "file_exists", "path": "proof.txt"})
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "session_id": "hook-green", "cwd": str(tmp_path),
        "hook_event_name": "Stop",
    })))

    assert main(["--root", str(tmp_path), "stop-hook"]) == 0
    event = _events(tmp_path, "hook-green")[-1]
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
    event = _events(tmp_path, "hook-red")[-1]
    assert event["claims_verdict"] == "RED"
    assert event["claims_unverified"][0]["claim"] == "missing proof exists"


def test_stop_hook_malformed_payload_never_breaks_shutdown(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-json"))
    assert main(["--root", str(tmp_path), "stop-hook"]) == 0
    assert "showwork stop-hook" in capsys.readouterr().err


def test_payload_session_id_rejects_non_scalar_types():
    """Lists/dicts/bools must not become str()-mangled session names."""
    from showwork.hooks import payload_session_id

    assert payload_session_id({"session_id": ["a", "b"]}) == "unknown-session"
    assert payload_session_id({"sessionId": {"x": 1}}) == "unknown-session"
    assert payload_session_id({"session_id": True}) == "unknown-session"
    assert payload_session_id({"session_id": "ok"}) == "ok"
    assert payload_session_id({"session_id": 42}) == "42"
    assert payload_session_id({}) == "unknown-session"


def test_stop_hook_prefers_showwork_session_env(tmp_path, monkeypatch):
    (tmp_path / "proof.txt").write_text("real", encoding="utf-8")
    record_claim(tmp_path, "task-slug", "proof exists",
                 check={"type": "file_exists", "path": "proof.txt"})
    monkeypatch.setenv("SHOWWORK_SESSION", "task-slug")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "session_id": "claude-host-uuid-ignored",
    })))
    assert main(["--root", str(tmp_path), "stop-hook"]) == 0
    event = _events(tmp_path, "task-slug")[-1]
    assert event["session"] == "task-slug"
    assert event["session_bound_from"] == "SHOWWORK_SESSION"
    assert event["hook_payload_session"] == "claude-host-uuid-ignored"
    assert event["claims_verdict"] == "GREEN"
    assert "session_unbound" not in event


def test_stop_hook_marks_unbound_payload_session(tmp_path, monkeypatch):
    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"session_id":"host-uuid-only"}'))
    assert main(["--root", str(tmp_path), "stop-hook"]) == 0
    event = _events(tmp_path, "host-uuid-only")[-1]
    assert event["session"] == "host-uuid-only"
    assert event["session_unbound"] is True
    assert event.get("session_bound_from") is None


def _stop(tmp_path, monkeypatch, session):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": session})))
    assert main(["--root", str(tmp_path), "stop-hook"]) == 0


def test_stop_hook_skips_repeat_observation(tmp_path, monkeypatch):
    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    for _ in range(3):
        _stop(tmp_path, monkeypatch, "repeat")
    assert len(_events(tmp_path, "repeat")) == 1


def test_stop_hook_records_again_when_verdict_changes(tmp_path, monkeypatch):
    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    record_claim(tmp_path, "flip", "proof exists",
                 check={"type": "file_exists", "path": "proof.txt"})
    _stop(tmp_path, monkeypatch, "flip")
    (tmp_path / "proof.txt").write_text("real", encoding="utf-8")
    _stop(tmp_path, monkeypatch, "flip")
    _stop(tmp_path, monkeypatch, "flip")
    assert [e["claims_verdict"] for e in _events(tmp_path, "flip")] == ["RED", "GREEN"]


def test_stop_hook_records_after_another_event(tmp_path, monkeypatch):
    from showwork.ledger import record_event

    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    _stop(tmp_path, monkeypatch, "between")
    record_event(tmp_path, "session.finish", "between", status="ok")
    _stop(tmp_path, monkeypatch, "between")
    events = _events(tmp_path, "between")
    assert len(events) == 3
    assert events[-1]["observed_by"] == "stop-hook"


def _start(tmp_path, monkeypatch, session, host):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", host)
    assert main(["--root", str(tmp_path), "start", "--session", session]) == 0


def test_start_records_host_session(tmp_path, monkeypatch):
    _start(tmp_path, monkeypatch, "task-a", "host-1")
    assert _events(tmp_path, "task-a")[0]["host_session"] == "host-1"


def test_stop_hook_binds_to_session_started_by_same_host(tmp_path, monkeypatch):
    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    _start(tmp_path, monkeypatch, "task-a", "host-1")
    _stop(tmp_path, monkeypatch, "host-1")
    event = _events(tmp_path, "task-a")[-1]
    assert event["observed_by"] == "stop-hook"
    assert event["session_bound_from"] == "host_session"
    assert event["hook_payload_session"] == "host-1"
    assert "session_unbound" not in event
    assert not sessions_path(tmp_path, "host-1").exists()


def test_stop_hook_ignores_other_hosts_open_session(tmp_path, monkeypatch):
    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    _start(tmp_path, monkeypatch, "agent-a-task", "host-a")
    _start(tmp_path, monkeypatch, "agent-b-task", "host-b")
    _stop(tmp_path, monkeypatch, "host-a")
    assert _events(tmp_path, "agent-a-task")[-1]["session_bound_from"] == "host_session"
    assert len(_events(tmp_path, "agent-b-task")) == 1


def test_stop_hook_binds_to_hosts_latest_start(tmp_path, monkeypatch):
    from showwork import ledger

    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    monkeypatch.setattr(ledger, "_now", lambda: "2026-01-01T00:00:01")
    _start(tmp_path, monkeypatch, "aa-later", "host-1")
    monkeypatch.setattr(ledger, "_now", lambda: "2026-01-01T00:00:00")
    _start(tmp_path, monkeypatch, "zz-earlier", "host-1")
    _stop(tmp_path, monkeypatch, "host-1")
    assert _events(tmp_path, "aa-later")[-1]["observed_by"] == "stop-hook"
    assert len(_events(tmp_path, "zz-earlier")) == 1


def test_stop_hook_unbound_after_explicit_finish(tmp_path, monkeypatch):
    from showwork.ledger import record_event

    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    _start(tmp_path, monkeypatch, "done-task", "host-1")
    record_event(tmp_path, "session.finish", "done-task", status="ok")
    _stop(tmp_path, monkeypatch, "host-1")
    assert len(_events(tmp_path, "done-task")) == 2
    assert _events(tmp_path, "host-1")[-1]["session_unbound"] is True


def test_stop_hook_stays_bound_after_refused_finish(tmp_path, monkeypatch):
    from showwork.ledger import record_event

    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    _start(tmp_path, monkeypatch, "refused-task", "host-1")
    record_event(tmp_path, "session.finish.refused", "refused-task")
    _stop(tmp_path, monkeypatch, "host-1")
    assert _events(tmp_path, "refused-task")[-1]["observed_by"] == "stop-hook"


def test_stop_hook_same_second_host_starts_bind_nothing(tmp_path, monkeypatch):
    from showwork import ledger

    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    monkeypatch.setattr(ledger, "_now", lambda: "2026-01-01T00:00:00")
    _start(tmp_path, monkeypatch, "task-a", "host-1")
    _start(tmp_path, monkeypatch, "task-b", "host-1")
    _stop(tmp_path, monkeypatch, "host-1")
    assert len(_events(tmp_path, "task-a")) == 1
    assert len(_events(tmp_path, "task-b")) == 1
    assert _events(tmp_path, "host-1")[-1]["session_unbound"] is True


def test_run_records_host_session(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "host-1")
    main(["--root", str(tmp_path), "run", "--session", "wrapped", "--agent", "x",
          "--", sys.executable, "-c", "pass"])
    assert _events(tmp_path, "wrapped")[0]["host_session"] == "host-1"
