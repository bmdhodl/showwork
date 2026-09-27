"""REGRESSION: main advancing must not add other PRs' receipts to this PR."""

import subprocess

import pytest

from showwork.ledger import start_session
from showwork.outcomes import changed_sessions


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True,
            check=True,
        ).stdout.strip()

    git("init")
    git("config", "user.name", "Receipt test")
    git("config", "user.email", "test@example.invalid")
    git("commit", "--allow-empty", "-m", "base")
    git("branch", "upstream")
    git("checkout", "-b", "topic")
    return tmp_path, git


def test_pr_selection_excludes_receipts_only_added_to_upstream(repo):
    root, git = repo
    start_session(root, "topic-work")
    git("add", ".showwork")
    git("commit", "-m", "topic receipt")
    git("checkout", "upstream")
    start_session(root, "other-pr")
    git("add", ".showwork")
    git("commit", "-m", "unrelated receipt")
    git("checkout", "topic")
    assert changed_sessions(root, "upstream") == ["topic-work"]


def test_upstream_receipt_is_not_proof_for_pr_without_receipt(repo):
    root, git = repo
    git("commit", "--allow-empty", "-m", "topic without receipt")
    git("checkout", "upstream")
    start_session(root, "other-pr")
    git("add", ".showwork")
    git("commit", "-m", "unrelated receipt")
    git("checkout", "topic")
    with pytest.raises(ValueError, match="no changed session receipt"):
        changed_sessions(root, "upstream")


def test_deleted_receipt_uses_fork_point_even_if_upstream_changed_it(repo):
    root, git = repo
    start_session(root, "removed")
    git("add", ".showwork")
    git("commit", "-m", "shared receipt")
    git("branch", "-f", "upstream", "HEAD")
    git("rm", "-r", ".showwork")
    git("commit", "-m", "delete receipt on topic")
    git("checkout", "upstream")
    git("rm", "-r", ".showwork")
    git("commit", "-m", "delete receipt upstream too")
    git("checkout", "topic")
    assert changed_sessions(root, "upstream") == ["removed"]


def test_missing_base_is_actionable(repo):
    root, _ = repo
    with pytest.raises(ValueError, match="fetch-depth: 0"):
        changed_sessions(root, "missing-revision")
