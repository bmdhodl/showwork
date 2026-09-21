"""Receipt explanations: same fields in text and JSON, no second ledger."""
from __future__ import annotations

import json

from showwork.checks import evaluate_records
from showwork.explain import explain_state, redact, render_explanation, row_class
from showwork.outcomes import outcome_summary
from showwork.receipts import _payload, render_badges_html
from showwork.report import render_status


def _state(results, *, verdict="GREEN"):
    state = {
        "label": "fixture",
        "verdict": verdict,
        "passed": sum(row["status"] == "pass" for row in results),
        "total": len(results),
        "results": results,
        "gaps": [],
    }
    state["outcome"] = outcome_summary(state)
    return state


def test_text_and_json_share_requirement_check_scope_and_revision():
    results = [{
        "claim": "add(2, 2) returns 4",
        "requirement_id": "add",
        "scope": "behavior",
        "type": "command",
        "status": "pass",
        "detail": "exit 0, stdout has 'passed'",
        "evidence": {"git_commit": "abcdef1234567890"},
    }]
    explanation = explain_state(_state(results))
    text = render_explanation(explanation)
    blob = json.dumps(explanation)
    assert "requirement:add(2, 2) returns 4" in text
    assert "check:command" in text
    assert "scope:behavior" in text
    assert "result:pass" in text
    assert "evidence:requirement:add" in text
    assert "revision:abcdef123456" in text
    assert "undeclared requirements: unknown" in text
    assert "current_rerun" in text
    assert "Historical finish: absent" in text
    assert "Integrity: unknown" in text
    for key in ("requirement_id", "evidence_ref", "revision", "limitations"):
        assert key in blob
    assert explanation["outcome_verdict"] == "VERIFIED"


def test_incomplete_receipt_stays_unverified():
    """REGRESSION: pretty text must not grant a clean outcome."""
    state = _state([{
        "claim": "file exists",
        "type": "file_exists",
        "status": "pass",
        "detail": "there.txt exists",
    }])
    explanation = explain_state(state)
    assert state["outcome"]["verdict"] == "UNVERIFIED"
    assert explanation["outcome_verdict"] == "UNVERIFIED"
    assert "VERIFIED" != explanation["outcome_verdict"]
    assert "does not authorize a merge" in explanation["recovery"]


def test_disabled_and_unsupported_are_not_labeled_failures():
    disabled = row_class({
        "type": "command",
        "status": "error",
        "policy_disabled": True,
        "detail": "check disabled by read-only verification policy",
    })
    unsupported = row_class({
        "type": "nope",
        "status": "error",
        "detail": "unknown check type 'nope'",
    })
    missing = row_class({
        "type": None,
        "status": "skipped",
        "detail": "no check spec (non-falsifiable); recorded only",
    })
    assert disabled == "disabled"
    assert unsupported == "unsupported"
    assert missing == "unknown"


def test_share_text_redacts_paths_and_secrets():
    raw = r"see C:\Users\patri\secret and /home/patri/key sk-abcdefghijklmnop"
    cleaned = redact(raw)
    assert "patri" not in cleaned
    assert "sk-" not in cleaned
    assert "<path>" in cleaned
    assert "<secret>" in cleaned
    assert len(redact("x" * 500)) <= 240


def test_badge_html_redacts_share_text():
    html = render_badges_html([{
        "title": "card",
        "verification": _payload("failed", {
            "claim": "add",
            "check": "command",
            "detail": r"C:\Users\patri\secret sk-abcdefghijklmnop",
            "session": "s",
            "explanation": explain_state({"verdict": "RED", "results": [], "outcome": {"verdict": "UNVERIFIED"}}),
        }),
    }])
    assert "patri" not in html
    assert "sk-" not in html
    assert "does not authorize a merge" in html


def test_unknown_badge_cannot_become_verified_by_explanation():
    payload = _payload("unknown", {
        "reason": "ledger unreadable",
        "explanation": {"outcome_verdict": "VERIFIED", "rows": []},
    })
    assert payload["state"] == "unknown"
    assert payload["explanation"]["outcome_verdict"] == "UNVERIFIED"


def test_status_separates_historical_finish_from_current_rerun():
    text = render_status({
        "root": "project",
        "sessions": [{
            "session": "s",
            "open": False,
            "started": True,
            "live_verdict": "RED",
            "live_passed": 0,
            "live_total": 1,
            "last_claims_verdict": "GREEN",
            "agent": None,
            "gaps": [],
        }],
    })
    assert "historical_finish=GREEN" in text
    assert "current_rerun=RED" in text


def test_live_file_check_explanation_matches_renderer(tmp_path):
    (tmp_path / "there.txt").write_text("x", encoding="utf-8")
    state = evaluate_records([{
        "session": "t",
        "claim": "there",
        "severity": "RED",
        "check": {"type": "file_exists", "path": "there.txt"},
    }], tmp_path, label="t")
    state["outcome"] = outcome_summary(state)
    from showwork.checks import render_report
    report = render_report(state)
    assert "Outcome: UNVERIFIED" in report
    assert "result:pass" in report
    assert "evidence:claim:0" in report
    assert "RED" not in report
