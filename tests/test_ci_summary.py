"""A check summary exposes coverage without rerunning or upgrading evidence."""

import json
import os
from pathlib import Path
import subprocess
import sys

from showwork.ci_summary import render_summary


SHA = "a" * 40


def receipt(session="one", *, status="pass", verdict="GREEN"):
    return {
        "session": session, "verdict": verdict, "errors": [],
        "historical_integrity": "GREEN",
        "checks": {
            "verdict": verdict,
            "outcome": {"verdict": "VERIFIED" if status == "pass" else "UNVERIFIED"},
            "results": [{
                "requirement_id": "write-read", "claim": "write survives reopen",
                "scope": "behavior", "type": "command", "status": status,
                "detail": "exit 0" if status == "pass" else "exit 1",
                "evidence": {"git_commit": SHA, "exit_code": 0 if status == "pass" else 1,
                             "stdout_sha256": "b" * 64},
            }],
        },
    }


def test_every_selected_session_links_requirement_receipt_and_observed_revision():
    """REGRESSION: the action printed a gate verdict with no requirement coverage."""
    summary = render_summary({"verdict": "RED", "sessions": [receipt(), receipt("two", status="fail", verdict="RED")]},
                             revision=SHA, repository="bmdhodl/showwork")
    assert ".showwork/sessions/one.jsonl" in summary
    assert ".showwork/sessions/two.jsonl" in summary
    assert f"https://github.com/bmdhodl/showwork/blob/{SHA}/" in summary
    assert "write-read" in summary and "write survives reopen" in summary
    assert "behavior" in summary and "pass" in summary and "fail" in summary
    assert "exit 1" in summary and "b" * 64 in summary
    assert "test adequacy: not assessed" in summary


def test_missing_disabled_and_prose_checks_stay_visible():
    row = receipt(status="error", verdict="RED")
    row["checks"]["results"][0].update(policy_disabled=True, detail="execution disabled", evidence={})
    empty = receipt("empty", verdict="RED")
    empty["checks"].update(results=[], outcome={"verdict": "UNVERIFIED"})
    summary = render_summary({"verdict": "RED", "sessions": [row, empty]}, revision=SHA)
    assert "disabled" in summary
    assert "No declared acceptance requirements" in summary
    assert "UNVERIFIED" in summary
    assert "not executed" in summary


def test_empty_or_malformed_results_cannot_display_an_accepted_outcome():
    for result in ({"verdict": "GREEN", "sessions": []}, {"verdict": "GREEN"}, {}, []):
        summary = render_summary(result, revision=SHA)
        assert "UNVERIFIED" in summary
        assert "No selected session receipts" in summary


def test_malformed_rows_and_links_stay_bounded_and_unknown():
    row = receipt()
    row["checks"]["results"] = None
    for server in ("https://github.com)evil", "https://[", "https://github.com/path"):
        summary = render_summary({"verdict": "GREEN", "sessions": [row]},
                                 revision=SHA, repository="../repo", server_url=server)
        assert "Outcome: UNVERIFIED" in summary
        assert "[receipt](" not in summary


def test_large_summary_discloses_omitted_rows_instead_of_hiding_coverage():
    row = receipt()
    row["checks"]["results"] *= 81
    summary = render_summary({"verdict": "GREEN", "sessions": [row]}, revision=SHA)
    assert "1 more requirements omitted from display" in summary


def test_actual_cli_gate_routes_its_result_to_summary_without_second_verification(tmp_path, monkeypatch, capsys):
    from showwork.cli import main
    from showwork import outcomes
    calls = []
    def gate(root, session, **kwargs):
        calls.append(session)
        return {**receipt(session), "integrity_scope": "selected session", "legacy_baseline": None}
    monkeypatch.setattr(outcomes, "release_gate", gate)
    monkeypatch.setattr(outcomes, "changed_sessions", lambda root, base: ["one", "two"])
    monkeypatch.setenv("SHOWWORK_CI_REPOSITORY", "bmdhodl/showwork")
    assert main(["--root", str(tmp_path), "gate", "--changed-since", "base"]) == 0
    output = capsys.readouterr().out
    assert calls == ["one", "two"]
    assert "Session one" in output and "Session two" in output
    assert "write-read" in output


def test_untrusted_text_and_link_parameters_cannot_inject_markdown_or_commands():
    row = receipt("../../bad")
    row["checks"]["results"][0]["claim"] = "<script> | [click](https://evil.test) sk-abcdefghijklmnop owner@example.test"
    summary = render_summary({"verdict": "RED", "sessions": [row]}, revision="main)",
                             repository="evil/../../repo", server_url="javascript:alert(1)")
    assert "<script>" not in summary
    assert "[click](https://evil.test)" not in summary
    assert "sk-abcdefghijklmnop" not in summary
    assert "owner@example.test" not in summary
    assert "javascript:" not in summary
    assert "https://evil.test)" not in summary
    assert "revision: unknown" in summary


def test_formatter_reads_json_without_launching_any_recorded_command(tmp_path):
    row = receipt()
    marker = tmp_path / "executed"
    row["checks"]["results"][0]["evidence"]["argv"] = ["python", str(marker)]
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    run = subprocess.run([sys.executable, "-m", "showwork.ci_summary", "--revision", SHA],
                         input=json.dumps({"verdict": "GREEN", "sessions": [row]}),
                         capture_output=True, text=True, env=env, timeout=20)
    assert run.returncode == 0, run.stderr
    assert "write-read" in run.stdout
    assert not marker.exists()


def test_invalid_json_is_a_visible_summary_error_with_no_acceptance():
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    run = subprocess.run([sys.executable, "-m", "showwork.ci_summary"], input="not json",
                         capture_output=True, text=True, env=env, timeout=20)
    assert run.returncode == 0
    assert "UNVERIFIED" in run.stdout and "could not read" in run.stdout
