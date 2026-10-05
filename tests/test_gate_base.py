"""REGRESSION: a merge from main must not read as the session's own change.

A branch that must be up to date before it merges takes main's edits after its
session started. The start snapshot then saw those edits as undeclared damage,
and every such pull request showed a RED receipt. Given a trusted base revision,
the gate excuses a changed file only when it now equals that base exactly.
"""

import json
import re
import subprocess

import pytest

from showwork.cli import main
from showwork.ledger import finish_session, record_claim, start_session
from showwork.outcomes import record_requirement

SESSION = "topic-work"


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True,
                              text=True, check=True).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "Receipt test")
    git("config", "user.email", "test@example.invalid")
    git("config", "core.autocrlf", "false")
    (tmp_path / "check.py").write_text('print("passed")\n')
    (tmp_path / "shared.py").write_text("value = 1\n")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "old.py").write_text("legacy = True\n")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    git("branch", "-M", "main")
    git("checkout", "-q", "-b", "topic")
    return tmp_path, git


def close_session(root, git, *, commit=True):
    """Make one declared change, close the session GREEN, commit its receipt."""
    start_session(root, SESSION)
    record_requirement(root, SESSION, "suite", "check.py passes", "behavior",
                       {"type": "command", "argv": ["python", "check.py"]})
    (root / "feature.py").write_text("feature = True\n")
    record_claim(root, SESSION, "feature.py exists",
                 {"type": "file_exists", "path": "feature.py"})
    assert finish_session(root, SESSION)[0] == 0
    if commit:
        git("add", "-A")
        git("commit", "-q", "-m", "topic work and receipt")


def change_on_main(root, git, path, text):
    """Commit a change on main and return to topic; text None deletes."""
    git("checkout", "-q", "main")
    if text is None:
        (root / path).unlink()
    else:
        (root / path).write_text(text)
    git("add", "-A")
    git("commit", "-q", "-m", f"main changes {path}")
    git("checkout", "-q", "topic")


def gate(root, capsys, *args):
    code = main(["--root", str(root), "gate", "--require-tracked", "--json", *args])
    return code, json.loads(capsys.readouterr().out)


def gate_text(root, capsys, *args):
    code = main(["--root", str(root), "gate", "--require-tracked", *args])
    return code, capsys.readouterr().out


def test_gate_base_excuses_a_file_that_only_main_changed(repo, capsys):
    root, git = repo
    close_session(root, git)
    change_on_main(root, git, "shared.py", "value = 2\n")
    git("merge", "-q", "--no-edit", "main")

    code, result = gate(root, capsys, "--session", SESSION)
    assert code == 2
    assert any("undeclared change: shared.py" in error for error in result["errors"])

    base = git("rev-parse", "main")
    code, result = gate(root, capsys, "--session", SESSION, "--base", "main")
    assert code == 0, result["errors"]
    assert result["sessions"][0]["base_matches"] == {"revision": base, "paths": ["shared.py"]}
    assert any("shared.py" in note and base[:12] in note for note in result["notes"])


def test_changed_since_uses_its_revision_as_the_base(repo, capsys):
    # The CI action passes the pull request's base SHA as changed-since.
    root, git = repo
    close_session(root, git)
    change_on_main(root, git, "shared.py", "value = 2\n")
    git("merge", "-q", "--no-edit", "main")
    code, result = gate(root, capsys, "--changed-since", git("rev-parse", "main"))
    assert code == 0, result["errors"]
    assert result["sessions"][0]["base_matches"]["paths"] == ["shared.py"]


def test_text_gate_prints_the_base_note_without_html_entities(repo, capsys):
    """REGRESSION: the terminal showed `the base&#x27;s change` in the base note."""
    root, git = repo
    close_session(root, git)
    change_on_main(root, git, "shared.py", "value = 2\n")
    git("merge", "-q", "--no-edit", "main")
    base = git("rev-parse", "main")
    code, output = gate_text(root, capsys, "--changed-since", base)
    assert code == 0, output
    assert f"shared.py changed since session.start and equals base {base[:12]}" in output
    assert not re.search(r"&#?\w+;", output), output


def test_text_gate_prints_each_session_error_once(repo, capsys):
    """REGRESSION: the text gate printed every session error again at the top level."""
    root, git = repo
    close_session(root, git)
    change_on_main(root, git, "shared.py", "value = 2\n")
    git("merge", "-q", "--no-edit", "main")
    (root / "shared.py").write_text("value = 3\n")
    git("commit", "-q", "-am", "topic edits shared.py after the merge")
    code, output = gate_text(root, capsys, "--changed-since", git("rev-parse", "main"))
    assert code == 2
    assert output.count("- declared acceptance checks are not verified") == 1, output
    assert output.count("- undeclared change: shared.py") == 1, output


def test_text_gate_keeps_an_error_that_no_session_reports(repo, capsys):
    root, git = repo
    close_session(root, git)
    code, output = gate_text(root, capsys, "--changed-since", "no-such-revision")
    assert code == 2
    assert "No selected session receipts" in output
    assert output.count("- cannot resolve a common receipt base") == 1, output


def test_gate_base_excuses_a_file_that_main_deleted(repo, capsys):
    root, git = repo
    close_session(root, git)
    change_on_main(root, git, "lib/old.py", None)
    git("merge", "-q", "--no-edit", "main")
    code, result = gate(root, capsys, "--session", SESSION)
    assert any("undeclared deletion: lib/old.py" in error for error in result["errors"])
    code, result = gate(root, capsys, "--session", SESSION, "--base", "main")
    assert code == 0, result["errors"]
    assert result["sessions"][0]["base_matches"]["paths"] == ["lib/old.py"]


def test_gate_base_accepts_a_crlf_checkout_of_the_base_file(repo, capsys):
    # Windows checkouts write CRLF; the base blob holds LF.
    root, git = repo
    close_session(root, git)
    change_on_main(root, git, "shared.py", "value = 2\n")
    git("merge", "-q", "--no-edit", "main")
    (root / "shared.py").write_bytes(b"value = 2\r\n")
    code, result = gate(root, capsys, "--session", SESSION, "--base", "main")
    assert code == 0, result["errors"]


def test_gate_base_still_flags_a_session_edit_to_a_file_main_changed(repo, capsys):
    root, git = repo
    close_session(root, git)
    change_on_main(root, git, "shared.py", "value = 2\n")
    git("merge", "-q", "--no-edit", "main")
    (root / "shared.py").write_text("value = 3\n")
    git("commit", "-q", "-am", "topic edits shared.py after the merge")
    code, result = gate(root, capsys, "--session", SESSION, "--base", "main")
    assert code == 2
    assert any("undeclared change: shared.py" in error for error in result["errors"])
    assert result["sessions"][0]["base_matches"]["paths"] == []


def test_gate_base_still_flags_an_edit_made_inside_the_merge(repo, capsys):
    # A conflict fix or an "evil merge" puts bytes in the merge that main never had.
    root, git = repo
    close_session(root, git)
    change_on_main(root, git, "shared.py", "value = 2\n")
    git("merge", "-q", "--no-commit", "--no-ff", "main")
    (root / "shared.py").write_text("value = 2  # tuned in the merge\n")
    git("add", "shared.py")
    git("commit", "-q", "--no-edit")
    code, result = gate(root, capsys, "--session", SESSION, "--base", "main")
    assert code == 2
    assert any("undeclared change: shared.py" in error for error in result["errors"])


def test_branch_forked_before_main_changed_cannot_excuse_reverting_it(repo, capsys):
    # The session recorded on main's newer tree, then the work was committed on
    # a stale branch. Its merge base still holds the old bytes; main does not.
    root, git = repo
    git("checkout", "-q", "main")
    (root / "shared.py").write_text("value = 2\n")
    git("commit", "-q", "-am", "main changes shared.py")
    close_session(root, git, commit=False)
    git("checkout", "-q", "topic")
    assert (root / "shared.py").read_text() == "value = 1\n"
    git("add", "-A")
    git("commit", "-q", "-m", "topic work and receipt on a stale branch")
    code, result = gate(root, capsys, "--session", SESSION, "--base", "main")
    assert code == 2
    assert any("undeclared change: shared.py" in error for error in result["errors"])


def test_gate_base_does_not_excuse_deleting_an_untracked_file(repo, capsys):
    # The base never had this file, so its absence there proves nothing.
    root, git = repo
    (root / ".git" / "info" / "exclude").write_text("notes.txt\n")
    (root / "notes.txt").write_text("local notes\n")
    close_session(root, git)
    (root / "notes.txt").unlink()
    code, result = gate(root, capsys, "--session", SESSION, "--base", "main")
    assert code == 2
    assert any("undeclared deletion: notes.txt" in error for error in result["errors"])


def test_gate_base_must_not_contain_head(repo, capsys):
    # Every committed change matches HEAD; such a base would excuse them all.
    root, git = repo
    close_session(root, git)
    code, result = gate(root, capsys, "--session", SESSION, "--base", "HEAD")
    assert code == 2
    assert any("contains HEAD" in error for error in result["errors"])


@pytest.mark.parametrize("args, message", [
    (["--base", "no-such-revision"], "cannot resolve base"),
    (["--base=-x"], "base must be a Git revision"),
])
def test_gate_base_rejects_an_unusable_revision(repo, capsys, args, message):
    root, git = repo
    close_session(root, git)
    code, result = gate(root, capsys, "--session", SESSION, *args)
    assert code == 2
    assert any(message in error for error in result["errors"])


def test_gate_base_and_changed_since_cannot_be_combined(repo, capsys):
    root, git = repo
    close_session(root, git)
    code, result = gate(root, capsys, "--changed-since", "main", "--base", "main")
    assert code == 2
    assert any("--changed-since already sets the base" in error for error in result["errors"])
