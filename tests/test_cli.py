"""End-to-end lifecycle tests through the CLI: start -> claim -> verify -> finish."""

import json

from showwork.cli import main
from showwork.ledger import sessions_path


def run(tmp_path, *argv):
    return main(["--root", str(tmp_path), *argv])


def test_full_green_lifecycle(tmp_path, capsys):
    (tmp_path / "out.md").write_text("shipped: yes", encoding="utf-8")
    assert run(tmp_path, "start", "--session", "s1", "--agent", "test") == 0
    assert run(tmp_path, "claim", "--session", "s1", "--claim", "wrote out.md",
               "--type", "file_contains", "--path", "out.md", "--pattern", "shipped") == 0
    assert run(tmp_path, "verify", "--session", "s1") == 0
    assert run(tmp_path, "finish", "--session", "s1") == 0
    out = capsys.readouterr().out
    assert "GREEN" in out
    assert "session.finish recorded" in out


def test_exit_gate_refuses_red_close(tmp_path, capsys):
    run(tmp_path, "start", "--session", "s2")
    run(tmp_path, "claim", "--session", "s2", "--claim", "made a file",
        "--type", "file_exists", "--path", "never-created.txt")
    assert run(tmp_path, "verify", "--session", "s2") == 2
    assert run(tmp_path, "finish", "--session", "s2") == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err
    events = [json.loads(l) for l in
              sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "session.finish.refused"


def test_retraction_unblocks_close(tmp_path):
    run(tmp_path, "start", "--session", "s3")
    run(tmp_path, "claim", "--session", "s3", "--claim", "made a file",
        "--type", "file_exists", "--path", "never-created.txt")
    assert run(tmp_path, "finish", "--session", "s3") == 2
    assert run(tmp_path, "retract", "--session", "s3", "--claim", "made a file",
               "--reason", "it never happened") == 0
    assert run(tmp_path, "finish", "--session", "s3") == 0


def test_no_verify_bypass_is_stamped(tmp_path):
    run(tmp_path, "start", "--session", "s4")
    run(tmp_path, "claim", "--session", "s4", "--claim", "made a file",
        "--type", "file_exists", "--path", "never-created.txt")
    assert run(tmp_path, "finish", "--session", "s4", "--no-verify") == 0
    events = [json.loads(l) for l in
              sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "session.finish"
    assert events[-1]["verify_bypassed"] is True


def test_blocked_close_does_not_gate(tmp_path):
    run(tmp_path, "start", "--session", "s5")
    run(tmp_path, "claim", "--session", "s5", "--claim", "made a file",
        "--type", "file_exists", "--path", "never-created.txt")
    assert run(tmp_path, "finish", "--session", "s5", "--status", "blocked") == 0


def test_prose_claim_records_but_does_not_verify(tmp_path, capsys):
    run(tmp_path, "start", "--session", "s6")
    assert run(tmp_path, "claim", "--session", "s6",
               "--claim", "I thought hard about the roadmap") == 0
    assert run(tmp_path, "verify", "--session", "s6") == 0  # skipped only => GREEN
    out = capsys.readouterr().out
    assert "not verifiable" in out


def test_verify_date_json_and_report(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    run(tmp_path, "claim", "--session", "s7", "--claim", "a exists",
        "--type", "file_exists", "--path", "a.txt")
    capsys.readouterr()  # flush the "claim recorded" line
    assert run(tmp_path, "verify", "--json") == 0
    state = json.loads(capsys.readouterr().out)
    assert state["verdict"] == "GREEN"
    reports = list((tmp_path / ".showwork").glob("audit-*.md"))
    assert reports, "verify should write a markdown audit report"


def test_unparseable_ledger_line_is_yellow_not_dropped(tmp_path):
    run(tmp_path, "claim", "--session", "s8", "--claim", "good",
        "--type", "glob_count", "--pattern", ".showwork/*.jsonl", "--op", ">=", "--n", "1")
    ledger = next((tmp_path / ".showwork").glob("claims-*.jsonl"))
    with ledger.open("a", encoding="utf-8") as f:
        f.write("{not json\n")
    assert run(tmp_path, "verify", "--no-report") == 3  # YELLOW, never silently GREEN


def test_check_json_passthrough(tmp_path):
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")
    check = json.dumps({"type": "file_contains", "path": "x.txt", "pattern": "hello"})
    assert run(tmp_path, "claim", "--session", "s9", "--claim", "x says hello",
               "--check-json", check) == 0
    assert run(tmp_path, "verify", "--session", "s9", "--no-report") == 0


def test_invalid_check_json_is_clean_error(tmp_path):
    """Malformed --check-json must not raise an uncaught JSONDecodeError.

    Agents and shell wrappers feed --check-json; a traceback is a vacuous
    failure (exit path unclear, message buried). Match other CLI validation:
    SystemExit with a clear message naming the flag.
    """
    try:
        run(tmp_path, "claim", "--session", "s-bad-json", "--claim", "x",
            "--check-json", "{not valid json")
    except SystemExit as e:
        msg = str(e)
        assert "--check-json" in msg
        assert "valid JSON" in msg or "not valid" in msg.lower()
    else:
        raise AssertionError("expected SystemExit for malformed --check-json")
