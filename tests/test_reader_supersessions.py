"""REGRESSION: the read-only badge failed a claim that `verify` had superseded.

Session A claimed that one plan note matched `notes/v1-*.md` and closed GREEN.
Session B renamed the note and recorded `showwork supersede` for A's claim.
`verify` and `gate` then skipped the claim and named B and the reason. The
receipts badge read only A's own rows, checked the claim again and showed A as
FAILED.
"""

import hashlib
import json
import subprocess
from pathlib import Path

from showwork import ledger
from showwork.cli import main
from showwork.ledger import finish_session, record_claim, session_claims_path, start_session
from showwork.outcomes import record_requirement
from showwork.reader import inspect_session
from showwork.receipts import evidence_for_session, render_badges_html

A = "bmd-notes-v1"
B = "bmd-notes-v2"
CLAIM = "one plan note matches notes/v1-*.md"
REASON = "the v2 release renames the plan note"
SUPERSEDED = f"superseded by session {B}: {REASON}"


def close_a(root):
    """Session A: claim the v1 note pattern and close GREEN."""
    (root / "anchor.txt").write_text("proof")
    (root / "notes").mkdir()
    start_session(root, A, agent="codex")
    record_requirement(root, A, "anchor", "anchor.txt exists", "artifact",
                       {"type": "file_exists", "path": "anchor.txt"})
    (root / "notes" / "v1-plan.md").write_text("plan")
    record_claim(root, A, CLAIM,
                 {"type": "glob_count", "pattern": "notes/v1-*.md", "op": "==", "n": 1})
    assert finish_session(root, A)[0] == 0


def open_b(root):
    """Session B: rename the note, so A's claim no longer holds."""
    start_session(root, B, agent="claude-code")
    (root / "notes" / "v1-plan.md").rename(root / "notes" / "v2-plan.md")
    record_claim(root, B, "the plan note moved to v2",
                 {"type": "path_moved", "from": "notes/v1-plan.md", "to": "notes/v2-plan.md"})


def supersede(root, capsys):
    code = main(["--root", str(root), "supersede", "--session", B, "--target-session", A,
                 "--claim", CLAIM, "--reason", REASON])
    output = capsys.readouterr()
    assert code == 0, output.out + output.err


def claim_ts(root):
    rows = [json.loads(line) for line in session_claims_path(root, A).read_text().splitlines()]
    return next(row["ts"] for row in rows if row.get("claim") == CLAIM)


def tree(root):
    return {path.relative_to(root).as_posix(): (hashlib.sha256(path.read_bytes()).hexdigest(),
                                                path.stat().st_mtime_ns)
            for path in sorted(root.rglob("*")) if path.is_file()}


def js_inspect(root, session):
    reader = (Path(__file__).resolve().parents[1] / "js/showwork-audit/reader.mjs").as_uri()
    code = (f"import {{inspectSession}} from {json.dumps(reader)}; "
            "console.log(JSON.stringify(inspectSession(process.argv[1], process.argv[2])));")
    proc = subprocess.run(["node", "--input-type=module", "-e", code, str(root), session],
                          capture_output=True, text=True, check=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return json.loads(proc.stdout)


def test_badge_honors_a_sound_supersession(tmp_path, capsys):
    close_a(tmp_path)
    open_b(tmp_path)

    # No marker: the badge checks A's claim again, and it fails.
    evidence = evidence_for_session(tmp_path, A)
    assert evidence["state"] == "failed"
    assert evidence["claim"] == CLAIM
    assert evidence["detail"] == "count 0 !== 1"
    assert evidence["superseded"] == []
    assert evidence["reader"]["supersessions"] == []

    supersede(tmp_path, capsys)
    before = tree(tmp_path)
    evidence = evidence_for_session(tmp_path, A)
    html = render_badges_html([{"verification": evidence, "title": "notes v1"}])
    assert tree(tmp_path) == before

    assert evidence["state"] == "verified"
    assert evidence["superseded"] == [
        {"claim": CLAIM, "superseded_by": B, "detail": SUPERSEDED}]
    reader = evidence["reader"]
    assert reader["manifest"] == "matches"
    assert reader["recorded_outcome"] == "VERIFIED"
    assert reader["supersessions"] == [
        {"claim": CLAIM, "ts": claim_ts(tmp_path), "by": B, "reason": REASON}]
    [row] = [row for row in evidence["explanation"]["rows"] if row["observed"] == SUPERSEDED]
    assert row["result"] == "skipped"
    assert f"Superseded claim: {CLAIM}; {SUPERSEDED}" in html
    assert 'data-state="verified"' in html

    # The badge and `verify` now agree on the same claim.
    assert main(["--root", str(tmp_path), "verify", "--no-report", "--json",
                 "--session", A]) == 0
    [verified] = [row for row in json.loads(capsys.readouterr().out)["results"]
                  if row["claim"] == CLAIM]
    assert (verified["status"], verified["superseded_by"], verified["detail"]) == (
        "skipped", B, SUPERSEDED)


def test_malformed_supersession_stays_an_error(tmp_path):
    close_a(tmp_path)
    open_b(tmp_path)
    # No reason: a checker error, never a skip.
    ledger._append(session_claims_path(tmp_path, B), {
        "session": B, "ts": "2026-10-05T12:00:00",
        "supersedes": {"session": A, "claim": CLAIM, "ts": claim_ts(tmp_path)}})

    evidence = evidence_for_session(tmp_path, A)
    assert evidence["state"] == "failed"
    assert evidence["claim"] == CLAIM
    assert evidence["superseded"] == []
    assert evidence["reader"]["supersessions"] == []

    writer = evidence_for_session(tmp_path, B)
    assert writer["state"] == "failed"
    assert writer["detail"] == ("invalid supersession record: "
                                "supersession_reason must not be empty")


def test_python_and_js_readers_name_the_same_supersession(tmp_path, capsys):
    close_a(tmp_path)
    open_b(tmp_path)
    for read in (inspect_session, js_inspect):
        result = read(tmp_path, A)
        assert result["recorded_outcome"] == "VERIFIED"
        assert result["supersessions"] == []

    supersede(tmp_path, capsys)
    target = {"session": A, "claim": CLAIM, "ts": claim_ts(tmp_path)}
    # A marker that pins no claim record, or a broken one, supersedes nothing.
    ledger._append(session_claims_path(tmp_path, B), {
        "session": B, "ts": "2026-10-05T12:00:00", "supersession_reason": REASON,
        "supersedes": {**target, "ts": "2000-01-01T00:00:00"}})
    ledger._append(session_claims_path(tmp_path, B), {
        "session": B, "ts": "2026-10-05T12:00:01", "supersession_reason": " \t",
        "supersedes": target})
    # Both readers trim the reason as Python's str.strip() does.
    ledger._append(session_claims_path(tmp_path, "bmd-notes-audit"), {
        "session": "bmd-notes-audit", "ts": "2026-10-05T12:00:02",
        "supersession_reason": f"\x1f{REASON}\x85", "supersedes": target})
    python, js = inspect_session(tmp_path, A), js_inspect(tmp_path, A)
    for result in (python, js):
        assert result["manifest"] == "matches"
        assert result["recorded_outcome"] == "VERIFIED"
    # File order: claims/bmd-notes-audit.jsonl sorts before B's file.
    assert python["supersessions"] == js["supersessions"] == [
        {"claim": CLAIM, "ts": target["ts"], "by": "bmd-notes-audit", "reason": REASON},
        {"claim": CLAIM, "ts": target["ts"], "by": B, "reason": REASON}]


def test_frozen_superseded_fixture_reads_verified():
    # js/showwork-audit/test.mjs reads the same bytes.
    fixture = Path(__file__).parent / "fixtures" / "readers" / "superseded"
    before = tree(fixture)
    evidence = evidence_for_session(fixture, "fixture")
    assert tree(fixture) == before
    assert evidence["state"] == "verified"
    assert evidence["superseded"] == [{
        "claim": CLAIM, "superseded_by": "later",
        "detail": f"superseded by session later: {REASON}"}]
    assert evidence["reader"]["supersessions"] == [{
        "claim": CLAIM, "ts": "2026-10-05T00:00:02", "by": "later", "reason": REASON}]
