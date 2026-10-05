"""Pytest temp folders stay out of the ledger that `git add .showwork/` commits."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def git_ignores(relpath):
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    result = subprocess.run(["git", "check-ignore", "--quiet", "--no-index", relpath],
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode == 128:
        pytest.skip("not a git checkout")
    return result.returncode == 0


@pytest.mark.parametrize("relpath", [
    ".showwork/pytest-tmp/test_x0/receipt.txt",
    ".showwork/pytest-tmp/claude-code-slug/test_x0/receipt.txt",
    ".showwork/pytest-tmp-qa064/test_x0/receipt.txt",
])
def test_pytest_temp_folders_are_ignored(relpath):
    assert git_ignores(relpath)


@pytest.mark.parametrize("relpath", [
    ".showwork/sessions/claude-code-slug.jsonl",
    ".showwork/claims/claude-code-slug.jsonl",
    ".showwork/snapshots/claude-code-slug.json",
])
def test_ledger_files_are_not_ignored(relpath):
    assert not git_ignores(relpath)
