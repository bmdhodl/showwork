"""REGRESSION: a later session must be able to acknowledge a same-day claim it breaks.

On 2026-10-05, session A claimed that ARCHITECTURE.md names version 0.6.5 and
closed. The 0.6.6 release changed that line the same day, so `showwork verify`
for the day went RED in the release pull request. The only remedy was to
retract A's claim. That appended to A's claims file, which selected A in the
receipts job and failed its gate: "receipt manifest differs". The release had
to wait for midnight UTC.

A supersession is written to the superseding session's own claims file. It
names one exact earlier claim of another session, says why it no longer holds,
and leaves the other session's receipt untouched.
"""

import json
import re
import subprocess

import pytest

from showwork import ledger
from showwork.cli import main
from showwork.ledger import (
    finish_session,
    record_claim,
    session_claims_path,
    session_events_path,
    start_session,
)
from showwork.outcomes import record_requirement
from showwork.report import analyze_fdr, session_status

DAY = "2026-10-05"
CODEX = "codex-architecture-current-version"
RELEASE = "claude-release-0-6-6"
PACKAGE = "Architecture names package version 0.6.5"
ACTION = "Architecture names action version 0.6.5"
REASON = "the 0.6.6 release moves ARCHITECTURE.md to 0.6.6"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    # Every record lands on one UTC day, as on the release runner.
    seconds = iter(range(1, 3600))

    def now():
        second = next(seconds)
        return f"{DAY}T00:{second // 60:02d}:{second % 60:02d}"

    monkeypatch.setattr(ledger, "_today", lambda: DAY)
    monkeypatch.setattr(ledger, "_now", now)

    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True,
                              text=True, check=True).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "Receipt test")
    git("config", "user.email", "test@example.invalid")
    git("config", "core.autocrlf", "false")
    (tmp_path / "check.py").write_text('print("passed")\n')
    write_versions(tmp_path, "0.6.4")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    git("branch", "-M", "main")
    return tmp_path, git


def write_versions(root, version):
    (root / "ARCHITECTURE.md").write_text(
        f"package version {version}\naction version {version}\n")


def version_check(kind, version):
    return {"type": "file_contains", "path": "ARCHITECTURE.md",
            "pattern": f"{kind} version {re.escape(version)}"}


def cli(root, capsys, *argv):
    code = main(["--root", str(root), *argv])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def verify_json(root, capsys, *argv):
    code = main(["--root", str(root), "verify", "--no-report", "--json", *argv])
    return code, json.loads(capsys.readouterr().out)


def gate(root, capsys, *argv):
    code = main(["--root", str(root), "gate", "--require-tracked", "--json", *argv])
    return code, json.loads(capsys.readouterr().out)


def supersede(root, capsys, claim, *, session=RELEASE, target=CODEX, reason=REASON):
    return cli(root, capsys, "supersede", "--session", session, "--target-session", target,
               "--claim", claim, "--reason", reason)


def close_codex_session(root, git):
    """Session A: claim the 0.6.5 lines, close GREEN, merge to main."""
    start_session(root, CODEX, agent="codex")
    record_requirement(root, CODEX, "suite", "check.py passes", "behavior",
                       {"type": "command", "argv": ["python", "check.py"]})
    write_versions(root, "0.6.5")
    record_claim(root, CODEX, PACKAGE, version_check("package", "0.6.5"))
    record_claim(root, CODEX, ACTION, version_check("action", "0.6.5"))
    assert finish_session(root, CODEX)[0] == 0
    git("add", "-A")
    git("commit", "-q", "-m", "codex: architecture names 0.6.5")


def open_release_session(root, git):
    """Session B: the release moves the same lines to 0.6.6 the same day."""
    git("checkout", "-q", "-b", "release")
    start_session(root, RELEASE, agent="claude")
    record_requirement(root, RELEASE, "suite", "check.py passes", "behavior",
                       {"type": "command", "argv": ["python", "check.py"]})
    write_versions(root, "0.6.6")
    record_claim(root, RELEASE, "Architecture names 0.6.6", {
        "type": "file_contains", "path": "ARCHITECTURE.md", "pattern": r"0\.6\.6"})


def close_release_session(root, git):
    assert finish_session(root, RELEASE)[0] == 0
    git("add", "-A")
    git("commit", "-q", "-m", "release 0.6.6 and receipt")


def receipt_bytes(root, session):
    return (session_claims_path(root, session).read_bytes(),
            session_events_path(root, session).read_bytes())


def rows_for(state, claim):
    return [row for row in state["results"] if row["claim"] == claim]


def test_same_day_supersession_keeps_verify_and_both_receipts_green(repo, capsys):
    root, git = repo
    close_codex_session(root, git)
    codex_receipt = receipt_bytes(root, CODEX)
    open_release_session(root, git)

    code, state = verify_json(root, capsys)
    assert code == 2
    assert [gap["claim"] for gap in state["gaps"]] == [PACKAGE, ACTION]

    for claim in (PACKAGE, ACTION):
        code, output = supersede(root, capsys, claim)
        assert code == 0, output
        assert "supersession recorded" in output

    code, output = cli(root, capsys, "verify", "--no-report")
    assert code == 0, output
    assert f"superseded by session {RELEASE}: {REASON}" in output
    code, state = verify_json(root, capsys)
    assert code == 0
    assert state["gaps"] == []
    for claim in (PACKAGE, ACTION):
        [row] = rows_for(state, claim)
        assert row["status"] == "skipped"
        assert row["superseded_by"] == RELEASE
        assert row["detail"] == f"superseded by session {RELEASE}: {REASON}"

    # The acknowledgment lives in the release session's file, not in A's.
    assert receipt_bytes(root, CODEX) == codex_receipt
    marker = json.loads(session_claims_path(root, RELEASE).read_text().splitlines()[-1])
    assert marker["session"] == RELEASE
    assert marker["supersedes"]["session"] == CODEX
    assert marker["supersedes"]["claim"] == ACTION
    assert marker["supersession_reason"] == REASON

    close_release_session(root, git)
    code, result = gate(root, capsys, "--changed-since", "main")
    assert code == 0, result["errors"]
    assert [row["session"] for row in result["sessions"]] == [RELEASE]
    assert any(f"supersedes {CODEX}" in note and REASON in note for note in result["notes"])

    # A's own receipt still passes when someone gates it directly.
    code, state = verify_json(root, capsys, "--session", CODEX)
    assert code == 0
    assert all(row["superseded_by"] == RELEASE
               for claim in (PACKAGE, ACTION) for row in rows_for(state, claim))
    assert session_status(root, CODEX)["sessions"][0]["live_verdict"] == "GREEN"
    code, result = gate(root, capsys, "--session", CODEX)
    assert code == 0, result["errors"]


def test_writing_into_another_sessions_claims_file_still_breaks_its_receipt(repo, capsys):
    # The #169 remedy. Supersession must not weaken this: a closed receipt
    # whose claims file changes afterwards stays RED.
    root, git = repo
    close_codex_session(root, git)
    open_release_session(root, git)
    for claim in (PACKAGE, ACTION):
        code, output = cli(root, capsys, "retract", "--session", CODEX,
                           "--claim", claim, "--reason", REASON)
        assert code == 0, output
    code, output = cli(root, capsys, "verify", "--no-report")
    assert code == 0, output
    close_release_session(root, git)

    code, result = gate(root, capsys, "--changed-since", "main")
    assert code == 2
    assert sorted(row["session"] for row in result["sessions"]) == sorted([CODEX, RELEASE])
    assert any("receipt manifest differs" in error for error in result["errors"])


def test_unacknowledged_contradiction_stays_red(repo, capsys):
    root, git = repo
    close_codex_session(root, git)
    open_release_session(root, git)

    code, output = supersede(root, capsys, PACKAGE)
    assert code == 0, output
    code, state = verify_json(root, capsys)
    assert code == 2
    assert [gap["claim"] for gap in state["gaps"]] == [ACTION]
    [row] = rows_for(state, PACKAGE)
    assert row["superseded_by"] == RELEASE

    # The supersession pins the exact record. The same text claimed again is
    # a new claim, and it fails again.
    record_claim(root, CODEX, PACKAGE, version_check("package", "0.6.5"))
    code, state = verify_json(root, capsys)
    assert code == 2
    assert [gap["claim"] for gap in state["gaps"]] == [ACTION, PACKAGE]
    assert [row["status"] for row in rows_for(state, PACKAGE)] == ["skipped", "fail"]


def test_supersede_refuses_targets_it_cannot_name(repo, capsys):
    root, git = repo
    close_codex_session(root, git)
    git("checkout", "-q", "-b", "release")
    release_file = session_claims_path(root, RELEASE)

    code, output = supersede(root, capsys, PACKAGE)
    assert code == 2
    assert "supersede rejected" in output and "start the session" in output

    start_session(root, RELEASE)
    record_claim(root, CODEX, "Architecture is current", {
        "type": "file_exists", "path": "ARCHITECTURE.md"})
    cli(root, capsys, "retract", "--session", CODEX,
        "--claim", "Architecture is current", "--reason", "it was not checked")
    refusals = [
        (dict(session=CODEX), "retract it instead"),
        (dict(claim="Architecture names version 9.9.9"), "has no claim"),
        (dict(target="nobody"), "has no claim"),
        (dict(reason="   "), "reason must not be empty"),
        (dict(claim="Architecture is current"), "is retracted"),
    ]
    for overrides, message in refusals:
        claim = overrides.pop("claim", PACKAGE)
        code, output = supersede(root, capsys, claim, **overrides)
        assert code == 2, overrides
        assert "supersede rejected" in output and message in output, output
    assert not release_file.exists()


def test_malformed_supersession_is_visible(repo, capsys):
    root, git = repo
    close_codex_session(root, git)
    open_release_session(root, git)
    target = {"session": CODEX, "claim": PACKAGE, "ts": f"{DAY}T00:00:01"}
    release_file = session_claims_path(root, RELEASE)
    ledger._append(release_file, {"session": RELEASE, "ts": f"{DAY}T01:00:00",
                                  "supersedes": target})
    ledger._append(release_file, {"session": RELEASE, "ts": f"{DAY}T01:00:01",
                                  "supersedes": target, "supersession_reason": REASON,
                                  "claim": "hidden", "check": {"type": "file_exists",
                                                               "path": "missing.txt"}})
    ledger._append(release_file, {"session": RELEASE, "ts": f"{DAY}T01:00:02",
                                  "supersedes": target, "supersession_reason": REASON,
                                  "retracted": True,
                                  "retracts": {"session": RELEASE, "claim": "x"}})
    ledger._append(session_claims_path(root, CODEX), {
        "session": CODEX, "ts": f"{DAY}T01:00:03",
        "supersedes": target, "supersession_reason": REASON})

    code, state = verify_json(root, capsys, "--date", DAY)
    invalid = [row for row in state["results"]
               if row["detail"].startswith("invalid supersession record")]
    assert len(invalid) == 4
    assert all(row["status"] == "error" for row in invalid)
    assert [gap["claim"] for gap in state["gaps"] if gap["status"] == "fail"] == [
        PACKAGE, ACTION]
    assert code == 2


def test_supersession_is_not_a_false_done(repo, capsys):
    # A retraction says a claim was wrong when made. A supersession says a
    # later change replaced it, so neither session counts as a false done.
    root, git = repo
    close_codex_session(root, git)
    open_release_session(root, git)
    for claim in (PACKAGE, ACTION):
        assert supersede(root, capsys, claim)[0] == 0
    close_release_session(root, git)
    fdr = analyze_fdr(root)
    assert fdr["false_done_session_ids"] == []
    assert fdr["sessions"][CODEX]["retractions"] == 0
    assert fdr["sessions"][RELEASE]["checked_claims"] == 1


def test_text_gate_prints_the_supersession_note_without_html_entities(repo, capsys):
    """REGRESSION: the text gate printed the superseded claim as `&#x27;...&#x27;`.

    The note quoted the claim with repr(), and the summary escapes each quote
    as an HTML entity. The text gate output is also the GitHub step summary,
    so the escape stays and the note carries no quotes of its own.
    """
    root, git = repo
    close_codex_session(root, git)
    open_release_session(root, git)
    for claim in (PACKAGE, ACTION):
        assert supersede(root, capsys, claim)[0] == 0
    close_release_session(root, git)

    code, output = cli(root, capsys, "gate", "--require-tracked", "--changed-since", "main")
    assert code == 0, output
    for claim in (PACKAGE, ACTION):
        assert f"{RELEASE}: supersedes {CODEX} claim: {claim}; reason: {REASON}" in output
    assert not re.search(r"&#?\w+;", output), output


def test_supersession_note_stays_escaped_in_the_step_summary(repo, capsys):
    # Claim and reason text come from the ledger. The text gate output goes to
    # the step summary, so neither may render as HTML or Markdown there. The
    # JSON note keeps the exact text for machine readers.
    claim = "<img src=x onerror=alert(1)> see [home](https://evil.test)"
    reason = "`code` *bold* | cell"
    root, git = repo
    start_session(root, CODEX, agent="codex")
    record_requirement(root, CODEX, "suite", "check.py passes", "behavior",
                       {"type": "command", "argv": ["python", "check.py"]})
    record_claim(root, CODEX, claim, {"type": "file_exists", "path": "ARCHITECTURE.md"})
    assert finish_session(root, CODEX)[0] == 0
    git("add", "-A")
    git("commit", "-q", "-m", "codex receipt")
    open_release_session(root, git)
    code, output = supersede(root, capsys, claim, reason=reason)
    assert code == 0, output
    close_release_session(root, git)

    code, output = cli(root, capsys, "gate", "--require-tracked", "--changed-since", "main")
    assert code == 0, output
    assert (r"claim: &lt;img src=x onerror=alert\(1\)&gt; see \[home\]\(https://evil.test\); "
            r"reason: \`code\` \*bold\* \| cell") in output
    assert "<img" not in output and "[home](" not in output
    code, result = gate(root, capsys, "--changed-since", "main")
    assert code == 0, result["errors"]
    assert f"{RELEASE}: supersedes {CODEX} claim: {claim}; reason: {reason}" in result["notes"]
