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


def test_fork_prs_get_isolated_behavior_and_clean_room_checks():
    # REGRESSION: all behavioral jobs were skipped for external contributions.
    clean_room = read_repo_file(".github", "workflows", "clean-room-action.yml")
    workflow = read_repo_file(".github", "workflows", "ci.yml")
    ordinary = workflow.split("  receipts:", 1)[0]
    for content in (clean_room, ordinary):
        assert "head.repo.full_name" not in content
        assert "permissions:\n  contents: read" in content
        assert "persist-credentials: false" in content
        assert "pull_request_target" not in content
        assert "self-hosted" not in content


def test_nightly_package_matrix_never_publishes():
    workflow = read_repo_file(".github", "workflows", "nightly.yml")
    for platform in ("ubuntu-latest", "windows-latest", "macos-latest"):
        assert platform in workflow
    for version in ("3.10", "3.11", "3.12", "3.13"):
        assert version in workflow
    assert "scripts/smoke_release.py" in workflow
    assert "scripts/run_tests.py" in workflow
    assert "schedule:" in workflow
    assert "contents: read" in workflow
    assert "id-token: write" not in workflow
    assert "gh-action-pypi-publish" not in workflow


def test_clean_room_tamper_uses_per_session_event_file():
    workflow = read_repo_file(".github", "workflows", "clean-room-action.yml")
    assert ".showwork/sessions/${SESSION}.jsonl" in workflow
    assert ".showwork/sessions.jsonl" not in workflow


def test_clean_room_fork_safe_uses_locked_python_script():
    workflow = read_repo_file(".github", "workflows", "clean-room-action.yml")
    assert "command-arg=-c" not in workflow
    assert "scripts/ok.py" in workflow


def test_receipt_action_sensitive_inputs_default_to_refusal():
    action = read_repo_file("actions", "verify", "action.yml")
    for name in ("allow-commands", "allow-network"):
        assert 'default: "false"' in input_block(action, name)
    assert "SHOWWORK_NO_COMMANDS" in action
    assert "SHOWWORK_NO_NETWORK" in action


def test_ci_receipt_job_reviews_changed_committed_outcomes_on_trusted_branches():
    workflow = read_repo_file(".github", "workflows", "ci.yml")
    assert 'allow-commands: "true"' in workflow
    assert 'require-tracked: "true"' in workflow
    assert 'changed-since:' in workflow
    assert 'github.event.pull_request.head.repo.full_name == github.repository' in workflow
    assert "allow-network" not in workflow
    receipts = workflow.split("  receipts:", 1)[1]
    assert "mode: advisory" in receipts
    assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in receipts
    assert "continue-on-error" not in receipts


def test_ci_and_publishing_use_github_hosted_runners():
    workflow = read_repo_file(".github", "workflows", "ci.yml")
    assert "actions/setup-node@" in workflow
    assert 'node-version: "24"' in workflow
    for name in ("ci.yml", "publish.yml", "clean-room-action.yml"):
        assert "self-hosted" not in read_repo_file(".github", "workflows", name)


def test_action_defaults_to_enforcement():
    action = read_repo_file("actions", "verify", "action.yml")
    assert 'args=(--root "$SW_ROOT" gate)' in action
    assert 'exit "$code"' in action
    assert 'default: "true"' in input_block(action, "require-tracked")
    assert 'default: "enforce"' in input_block(action, "mode")


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
