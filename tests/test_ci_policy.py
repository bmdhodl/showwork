"""Regression tests for the fork-safe receipt-action policy surface."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_repo_file(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def input_block(action: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:|^runs:)",
        action,
    )
    assert match, f"action input block missing: {name}"
    return match.group(0)


def test_clean_room_skips_fork_shaped_pull_requests():
    workflow = read_repo_file(".github", "workflows", "clean-room-action.yml")
    guard = (
        "if: github.event_name != 'pull_request' || "
        "github.event.pull_request.head.repo.full_name == github.repository"
    )
    assert guard in workflow


def test_receipt_action_sensitive_inputs_default_to_refusal():
    action = read_repo_file("actions", "verify", "action.yml")
    for name in ("allow-commands", "allow-network"):
        assert 'default: "false"' in input_block(action, name)
    assert "SHOWWORK_NO_COMMANDS" in action
    assert "SHOWWORK_NO_NETWORK" in action


def test_ci_receipt_gate_keeps_sensitive_opt_ins_disabled():
    workflow = read_repo_file(".github", "workflows", "ci.yml")
    assert "allow-commands stays false" in workflow
    assert "allow-network" not in workflow


def test_ci_js_conformance_uses_host_node_without_setup_action():
    workflow = read_repo_file(".github", "workflows", "ci.yml")
    assert "actions/setup-node@" not in workflow
    assert "Require host-provisioned Node.js 24" in workflow
    assert '[[ "$node_version" == v24.* ]]' in workflow


def test_action_strict_mode_turns_yellow_into_failure():
    action = read_repo_file("actions", "verify", "action.yml")
    assert '3) if [ "${SW_STRICT}" = "true" ]; then fail=1; fi' in action


def test_ci_checkout_and_documentation_preserve_pin_boundary():
    workflow = read_repo_file(".github", "workflows", "clean-room-action.yml")
    docs = read_repo_file("docs", "ci.md")
    assert re.search(r"uses: actions/checkout@[0-9a-f]{40}", workflow)
    assert "Do not run `@main` in a gate you trust." in docs


def test_publish_workflow_pins_external_actions():
    workflow = read_repo_file(".github", "workflows", "publish.yml")
    expected = {
        "actions/checkout": "11bd71901bbe5b1630ceea73d27597364c9af683",
        "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
        "pypa/gh-action-pypi-publish": "dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
    }
    for action, sha in expected.items():
        assert f"{action}@{sha}" in workflow
    assert not re.search(
        r"^\s+uses:\s+[^@\s]+@(?:v\d|release/)", workflow, re.MULTILINE
    )
