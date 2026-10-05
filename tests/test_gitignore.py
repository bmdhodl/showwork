"""Pytest temp folders stay out of the ledger that `git add .showwork/` commits."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def git_ignores(relpath, scratch):
    """Ask git in a scratch repo that holds only this repo's .gitignore, so the
    user's global excludes and .git/info/exclude cannot change the answer."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    if not (ROOT / ".gitignore").exists():
        pytest.skip("no .gitignore in this tree")
    repo = scratch / "ignore-check"
    repo.mkdir()
    shutil.copyfile(ROOT / ".gitignore", repo / ".gitignore")
    empty_config = scratch / "empty-gitconfig"
    empty_config.write_text("", encoding="utf-8")
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(empty_config), "GIT_CONFIG_NOSYSTEM": "1",
           "XDG_CONFIG_HOME": str(scratch / "no-xdg-config")}
    subprocess.run(["git", "init", "-q"], cwd=repo, env=env, check=True, capture_output=True)
    result = subprocess.run(["git", "check-ignore", "--quiet", "--no-index", relpath],
                            cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode in (0, 1), result.stderr
    return result.returncode == 0


@pytest.mark.parametrize("relpath", [
    ".showwork/pytest-tmp/test_x0/receipt.txt",
    ".showwork/pytest-tmp/claude-code-slug/test_x0/receipt.txt",
    ".showwork/pytest-tmp-qa064/test_x0/receipt.txt",
])
def test_pytest_temp_folders_are_ignored(relpath, tmp_path):
    assert git_ignores(relpath, tmp_path)


@pytest.mark.parametrize("relpath", [
    ".showwork/sessions/claude-code-slug.jsonl",
    ".showwork/claims/claude-code-slug.jsonl",
    ".showwork/snapshots/claude-code-slug.json",
])
def test_ledger_files_are_not_ignored(relpath, tmp_path):
    assert not git_ignores(relpath, tmp_path)


@pytest.mark.parametrize("source", ["excludesFile", "XDG_CONFIG_HOME"])
def test_user_ignore_rules_do_not_change_the_answer(source, tmp_path, monkeypatch):
    """REGRESSION: a user's global `.showwork/` rule made ledger files look ignored."""
    user_rules = tmp_path / "user" / "git" / "ignore"
    user_rules.parent.mkdir(parents=True)
    user_rules.write_text(".showwork/\n*.jsonl\n", encoding="utf-8")
    if source == "excludesFile":
        user_config = tmp_path / "user" / "gitconfig"
        user_config.write_text(f"[core]\n\texcludesFile = {user_rules.as_posix()}\n", encoding="utf-8")
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(user_config))
    else:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "user"))
    assert not git_ignores(".showwork/sessions/claude-code-slug.jsonl", tmp_path)
