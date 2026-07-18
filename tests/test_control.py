"""Tests for the Claude Code control adapters.

Two properties matter most and both are negative:
  - a gate must not block ordinary work (or it gets switched off)
  - a gate must not be talkable-past (or it is decoration)
"""

from __future__ import annotations

import json

import pytest

from showwork.control import (
    DEFAULT_RULES,
    ApprovalDecision,
    RiskPolicy,
    RiskRule,
    call_from_payload,
    evaluate_post_tool_use,
    evaluate_pre_tool_use,
    render_post_tool_use,
    render_pre_tool_use,
    replay,
)
from showwork.guards import StuckDetector


def pre(tool_name: str, **tool_input) -> dict:
    return {"tool_name": tool_name, "tool_input": tool_input, "session_id": "s1"}


# -- approval gate: things that MUST stop -----------------------------------


@pytest.mark.parametrize(
    "payload,expected_rule",
    [
        (pre("Write", file_path=".github/workflows/ci.yml"), "ci-workflow"),
        (pre("Edit", file_path="repo/.github/workflows/deploy.yml"), "ci-workflow"),
        (pre("Write", file_path=".env"), "secrets"),
        (pre("Write", file_path="app/.env.production"), "secrets"),
        (pre("Edit", file_path="supabase/migrations/003_add.sql"), "db-migration"),
        (pre("Bash", command="git push --force origin main"), "history-rewrite"),
        (pre("Bash", command="git reset --hard HEAD~3"), "history-rewrite"),
        (pre("Bash", command="rm -rf /var/data"), "destructive-delete"),
        (pre("Bash", command="twine upload dist/*"), "publish"),
        (pre("Bash", command="npm publish"), "publish"),
    ],
)
def test_risky_actions_require_approval(payload, expected_rule):
    decision = evaluate_pre_tool_use(payload)
    assert decision.blocked
    assert decision.rule == expected_rule
    assert decision.reason


def test_windows_path_separators_still_match():
    decision = evaluate_pre_tool_use(
        pre("Write", file_path="repo\\.github\\workflows\\ci.yml")
    )
    assert decision.blocked


# -- approval gate: things that MUST NOT stop -------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        pre("Read", file_path="src/app.py"),
        pre("Write", file_path="src/app.py"),
        pre("Edit", file_path="tests/test_app.py"),
        pre("Bash", command="pytest -q"),
        pre("Bash", command="git status"),
        pre("Bash", command="git push origin feature-branch"),  # normal push
        pre("Bash", command="rm build/artifact.o"),  # non-recursive, scoped
        pre("Grep", pattern="TODO"),
    ],
)
def test_ordinary_work_is_not_gated(payload):
    assert not evaluate_pre_tool_use(payload).blocked


def test_malformed_payloads_fail_open_not_crash():
    # A gate that raises on junk input takes the whole agent down with it.
    for bad in ({}, {"tool_name": None}, {"tool_name": 42}, {"tool_name": "Write"}):
        assert not evaluate_pre_tool_use(bad).blocked


def test_rule_with_no_discriminator_never_matches_everything():
    empty = RiskRule(name="bad", reason="misconfigured")
    policy = RiskPolicy(rules=[empty])
    assert not policy.evaluate("Write", {"file_path": "anything.py"}).blocked


def test_deny_mode_for_unattended_runs():
    policy = RiskPolicy(behavior="deny")
    decision = policy.evaluate("Write", {"file_path": ".github/workflows/ci.yml"})
    assert decision.behavior == "deny"


# -- hook contract ----------------------------------------------------------


def test_pre_tool_use_output_matches_claude_code_contract():
    decision = evaluate_pre_tool_use(pre("Write", file_path=".env"))
    payload = json.loads(render_pre_tool_use(decision))
    hook = payload["hookSpecificOutput"]
    assert hook["hookEventName"] == "PreToolUse"
    assert hook["permissionDecision"] == "ask"
    assert "showwork:secrets" in hook["permissionDecisionReason"]


def test_allow_output_carries_no_reason():
    payload = json.loads(render_pre_tool_use(ApprovalDecision(behavior="allow")))
    assert payload["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "permissionDecisionReason" not in payload["hookSpecificOutput"]


def test_stuck_output_halts_the_loop():
    detector = StuckDetector(repeat_threshold=2)
    payloads = [pre("Read", file_path="a.py")] * 2
    verdict = replay(payloads, detector)
    out = json.loads(render_post_tool_use(verdict))
    assert out["continue"] is False
    assert "showwork:stuck:repeat" in out["stopReason"]


def test_healthy_run_continues():
    out = json.loads(render_post_tool_use(replay([pre("Read", file_path="a.py")])))
    assert out["continue"] is True


# -- mutation inference -----------------------------------------------------


def test_write_counts_as_progress():
    assert call_from_payload(pre("Write", file_path="a.py")).mutated


def test_read_does_not_count_as_progress():
    assert not call_from_payload(pre("Read", file_path="a.py")).mutated


@pytest.mark.parametrize(
    "command", ["ls -la", "git status", "pytest -q", "cat README.md", "grep -r x ."]
)
def test_readonly_shell_commands_do_not_count_as_progress(command):
    # Otherwise an agent could spin on `ls` forever and never trip no_progress.
    assert not call_from_payload(pre("Bash", command=command)).mutated


@pytest.mark.parametrize("command", ["python build.py", "mv a b", "touch new.py"])
def test_side_effecting_shell_commands_count_as_progress(command):
    assert call_from_payload(pre("Bash", command=command)).mutated


# -- end to end -------------------------------------------------------------


def test_agent_looping_on_a_failing_test_is_halted():
    detector = StuckDetector(repeat_threshold=3, no_progress_threshold=6)
    stream = [pre("Bash", command="pytest -q")] * 3
    verdict = replay(stream, detector)
    assert verdict.stuck
    assert verdict.reason == "repeat"


def test_agent_fixing_and_retesting_is_never_halted():
    """The real workflow: edit, run tests, edit, run tests."""
    detector = StuckDetector(repeat_threshold=3, no_progress_threshold=6)
    stream = []
    for i in range(12):
        stream.append(pre("Edit", file_path=f"src/fix{i}.py"))
        stream.append(pre("Bash", command="pytest -q"))
    assert not replay(stream, detector).stuck


def test_default_rules_are_all_well_formed():
    for rule in DEFAULT_RULES:
        assert rule.name and rule.reason
        assert rule.path_globs or rule.command_pattern or rule.tools
