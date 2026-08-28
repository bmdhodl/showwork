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
    events = [json.loads(line) for line in
              sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "session.finish.refused"


def test_retraction_unblocks_close(tmp_path):
    run(tmp_path, "start", "--session", "s3")
    run(tmp_path, "claim", "--session", "s3", "--claim", "made a file",
        "--type", "file_exists", "--path", "never-created.txt")
    assert run(tmp_path, "finish", "--session", "s3") == 2
    assert run(tmp_path, "retract", "--session", "s3", "--claim", "made a file",
               "--reason", "it never happened") == 0
    # Minimum-proof: retracting alone leaves no check-backed claims; re-claim.
    (tmp_path / "real.txt").write_text("ok", encoding="utf-8")
    assert run(tmp_path, "claim", "--session", "s3", "--claim", "wrote real.txt",
               "--type", "file_exists", "--path", "real.txt") == 0
    assert run(tmp_path, "finish", "--session", "s3") == 0


def test_exit_gate_refuses_empty_session(tmp_path, capsys):
    run(tmp_path, "start", "--session", "empty")
    assert run(tmp_path, "finish", "--session", "empty") == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err
    assert "no_check_backed_claims" in err
    events = [json.loads(line) for line in
              sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "session.finish.refused"
    assert events[-1]["refuse_reason"] == "no_check_backed_claims"
    assert events[-1]["claims_unverified"]


def test_exit_gate_refuses_prose_only_session(tmp_path):
    run(tmp_path, "start", "--session", "prose")
    run(tmp_path, "claim", "--session", "prose", "--claim", "vibes only")
    assert run(tmp_path, "finish", "--session", "prose") == 2
    events = [json.loads(line) for line in
              sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    assert events[-1]["refuse_reason"] == "no_check_backed_claims"


def test_refused_finish_records_claims_unverified(tmp_path):
    run(tmp_path, "start", "--session", "s-gap")
    run(tmp_path, "claim", "--session", "s-gap", "--claim", "made a file",
        "--type", "file_exists", "--path", "never-created.txt")
    assert run(tmp_path, "finish", "--session", "s-gap") == 2
    events = [json.loads(line) for line in
              sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    refused = events[-1]
    assert refused["event"] == "session.finish.refused"
    assert refused["refuse_reason"] == "claims_red"
    assert refused["claims_unverified"][0]["claim"] == "made a file"
    assert refused["claims_unverified"][0]["type"] == "file_exists"


def test_claim_rejects_invalid_command_shape(tmp_path, capsys):
    run(tmp_path, "start", "--session", "bad-cmd")
    code = run(tmp_path, "claim", "--session", "bad-cmd", "--claim", "ran git",
               "--check-json",
               json.dumps({"type": "command", "argv": ["git", "status"]}))
    assert code == 2
    assert "claim rejected" in capsys.readouterr().err
    # Nothing appended for the rejected claim.
    from showwork.ledger import claims_for_session
    assert claims_for_session(tmp_path, "bad-cmd") == []


def test_claim_rejects_bad_glob_op(tmp_path, capsys):
    code = run(tmp_path, "claim", "--session", "g", "--claim", "count",
               "--check-json",
               json.dumps({"type": "glob_count", "pattern": "*.md", "op": "eq", "n": 1}))
    assert code == 2
    assert "eq" in capsys.readouterr().err


def test_claim_warns_on_brittle_pass_count(tmp_path, capsys):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run_tests.py").write_text("print('ok')\n", encoding="utf-8")
    code = run(tmp_path, "claim", "--session", "w", "--claim", "tests",
               "--type", "command",
               "--command-arg", "python", "--command-arg", "scripts/run_tests.py",
               "--expect-exit", "0", "--stdout-contains", "42 passed")
    assert code == 0
    assert "goes stale" in capsys.readouterr().err


def test_status_and_report_smoke(tmp_path, capsys):
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    run(tmp_path, "start", "--session", "s-rep", "--agent", "test")
    run(tmp_path, "claim", "--session", "s-rep", "--claim", "f",
        "--type", "file_exists", "--path", "f.txt")
    run(tmp_path, "finish", "--session", "s-rep")
    capsys.readouterr()
    assert run(tmp_path, "status", "--session", "s-rep", "--json") == 0
    status = json.loads(capsys.readouterr().out)
    assert status["sessions"][0]["live_verdict"] == "GREEN"
    assert run(tmp_path, "report", "--json") == 0
    report = json.loads(capsys.readouterr().out)
    assert report["fdr"]["eligible_sessions"] == 1
    assert report["agents"]["test"] == 1


def test_no_verify_bypass_is_stamped(tmp_path):
    run(tmp_path, "start", "--session", "s4")
    run(tmp_path, "claim", "--session", "s4", "--claim", "made a file",
        "--type", "file_exists", "--path", "never-created.txt")
    assert run(tmp_path, "finish", "--session", "s4", "--no-verify") == 0
    events = [json.loads(line) for line in
              sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "session.finish"
    assert events[-1]["verify_bypassed"] is True


def test_blocked_close_does_not_gate(tmp_path):
    run(tmp_path, "start", "--session", "s5")
    run(tmp_path, "claim", "--session", "s5", "--claim", "made a file",
        "--type", "file_exists", "--path", "never-created.txt")
    assert run(tmp_path, "finish", "--session", "s5", "--status", "blocked") == 0


def test_finish_status_ok_is_case_insensitive_gate(tmp_path):
    """Python API status='OK' must still run the exit gate.

    CLI choices only allow lowercase ok|blocked, but finish_session is public.
    Pre-fix, status == 'ok' was case-sensitive, so status='OK' skipped
    verification, wrote session.finish with exit 0, and left no verify_bypassed
    stamp — a silent clean close over RED claims.
    """
    from showwork.ledger import finish_session, record_claim, start_session

    start_session(tmp_path, "s-case")
    record_claim(tmp_path, "s-case", "made a file",
                 check={"type": "file_exists", "path": "never-created.txt"})
    code, state = finish_session(tmp_path, "s-case", status="OK")
    assert code == 2
    assert state is not None and state["verdict"] == "RED"
    events = [json.loads(line) for line in
              sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "session.finish.refused"
    assert events[-1]["status"] == "ok"


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


def test_verify_report_stays_under_ledger_dir(tmp_path):
    """Session labels with path separators must not escape .showwork/.

    verify writes audit-<label>.md under the ledger dir. A label containing
    '..' / '\\' / '/' was joined into a multi-segment path, so the report
    could be created outside .showwork/ (e.g. project root or beyond).
    """
    # Enough .. segments to leave .showwork/ when treated as path parts.
    session = "..\\..\\..\\escaped-report"
    run(tmp_path, "claim", "--session", session, "--claim", "x",
        "--type", "file_exists", "--path", "nope.txt")
    assert run(tmp_path, "verify", "--session", session) == 2
    ledger = (tmp_path / ".showwork").resolve()
    # Report must exist under the ledger dir as a single file, not outside.
    reports = list(ledger.glob("audit-*.md"))
    assert reports, "expected a sanitized audit report under .showwork/"
    for report in reports:
        report.resolve().relative_to(ledger)
    # Must not have written the escape target at project root.
    assert not (tmp_path / "escaped-report.md").exists()
    assert not list(tmp_path.glob("escaped-report*"))


def test_unparseable_ledger_line_is_yellow_not_dropped(tmp_path):
    run(tmp_path, "claim", "--session", "s8", "--claim", "good",
        "--type", "glob_count", "--pattern", ".showwork/*.jsonl", "--op", ">=", "--n", "1")
    ledger = next((tmp_path / ".showwork").glob("claims-*.jsonl"))
    with ledger.open("a", encoding="utf-8") as f:
        f.write("{not json\n")
    assert run(tmp_path, "verify", "--no-report") == 3  # YELLOW, never silently GREEN



def test_non_object_ledger_line_is_yellow_not_crash(tmp_path):
    """JSONL lines that parse as non-objects must not AttributeError."""
    run(tmp_path, "claim", "--session", "s-nonobj", "--claim", "good",
        "--type", "glob_count", "--pattern", ".showwork/*.jsonl", "--op", ">=", "--n", "1")
    ledger = next((tmp_path / ".showwork").glob("claims-*.jsonl"))
    with ledger.open("a", encoding="utf-8") as f:
        f.write('"just a string"\n')
        f.write("[1, 2]\n")
        f.write("42\n")
    assert run(tmp_path, "verify", "--no-report") == 3  # YELLOW


def test_verify_date_rejects_path_escape(tmp_path):
    """--date must be YYYY-MM-DD; path segments must not escape .showwork/.

    claims_path was `claims-{date}.jsonl` with no validation, so a date like
    `..\\..\\passwd` resolved outside the ledger directory.
    """
    from showwork.ledger import claims_path

    try:
        claims_path(tmp_path, "..\\..\\passwd")
    except ValueError as e:
        assert "YYYY-MM-DD" in str(e) or "date" in str(e).lower()
    else:
        raise AssertionError("expected ValueError for path-like date")

    try:
        run(tmp_path, "verify", "--date", "..\\..\\passwd", "--no-report")
    except SystemExit as e:
        assert "date" in str(e).lower() or "YYYY-MM-DD" in str(e)
    else:
        raise AssertionError("expected SystemExit for hostile --date")


def test_check_json_passthrough(tmp_path):
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")
    check = json.dumps({"type": "file_contains", "path": "x.txt", "pattern": "hello"})
    assert run(tmp_path, "claim", "--session", "s9", "--claim", "x says hello",
               "--check-json", check) == 0
    assert run(tmp_path, "verify", "--session", "s9", "--no-report") == 0


def test_http_probe_claim_flags_are_recorded(tmp_path):
    assert run(
        tmp_path,
        "claim", "--session", "s-http", "--claim", "health endpoint is live",
        "--type", "http_probe", "--url", "https://example.com/health",
        "--expect-status", "200", "--body-contains", "ok",
    ) == 0
    claims = next((tmp_path / ".showwork").glob("claims-*.jsonl"))
    record = json.loads(claims.read_text(encoding="utf-8").splitlines()[0])
    assert record["check"] == {
        "type": "http_probe", "url": "https://example.com/health",
        "expect_status": 200, "body_contains": "ok",
    }


def test_git_state_claim_flags_are_recorded(tmp_path):
    assert run(
        tmp_path,
        "claim", "--session", "s-git", "--claim", "tree is clean",
        "--type", "git_state", "--clean", "--branch", "main",
        "--commit", "abcdef123456",
    ) == 0
    claims = next((tmp_path / ".showwork").glob("claims-*.jsonl"))
    record = json.loads(claims.read_text(encoding="utf-8").splitlines()[0])
    assert record["check"] == {
        "type": "git_state", "clean": True, "branch": "main",
        "commit": "abcdef123456",
    }


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

def test_invalid_utf8_ledger_verify_is_yellow_not_crash(tmp_path, capsys):
    """Non-UTF-8 ledger bytes must not raise UnicodeDecodeError from verify."""
    run(tmp_path, "claim", "--session", "s-utf8", "--claim", "good",
        "--type", "glob_count", "--pattern", ".showwork/*.jsonl", "--op", ">=", "--n", "1")
    capsys.readouterr()
    ledger = next((tmp_path / ".showwork").glob("claims-*.jsonl"))
    with ledger.open("ab") as f:
        f.write(b"\xff\xfe not utf-8\n")
    code = run(tmp_path, "verify", "--no-report", "--json")
    assert code == 3  # YELLOW
    state = json.loads(capsys.readouterr().out)
    assert state["verdict"] == "YELLOW"
    assert any(
        r["status"] == "error" and "utf-8" in r["detail"].lower()
        for r in state["results"]
    )



def test_invalid_utf8_blocks_append_with_clear_error(tmp_path):
    """Append after binary corruption must raise ValueError, not UnicodeDecodeError."""
    from showwork.ledger import record_claim

    record_claim(tmp_path, "s", "first")
    ledger = next((tmp_path / ".showwork").glob("claims-*.jsonl"))
    with ledger.open("ab") as f:
        f.write(b"\xff\xfe\n")
    try:
        record_claim(tmp_path, "s", "second")
    except ValueError as e:
        assert "utf-8" in str(e).lower()
    else:
        raise AssertionError("expected ValueError for non-UTF-8 ledger on append")


