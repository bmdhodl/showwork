"""Explicit adoption cannot turn damaged history into a valid current receipt."""

import json
import subprocess

import pytest

from showwork.audit import audit_root
from showwork.cli import main
from showwork.ledger import finish_session, record_claim, start_session
from showwork.outcomes import record_requirement, release_gate


LEGACY = ".showwork/claims-2026-01-01.jsonl"
BAD = json.dumps({"session": "old", "claim": "historical", "prev": "not-a-hash"}) + "\n"


def git(root, *args, **kwargs):
    return subprocess.run(["git", *args], cwd=root, capture_output=True,
                          text=True, check=True, **kwargs).stdout.strip()


def project(root, *, legacy=BAD, script='print("checked")\n', per_session_bad=False):
    git(root, "init")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "core.autocrlf", "false")
    (root / ".showwork").mkdir()
    if legacy is not None:
        (root / LEGACY).write_text(legacy, encoding="utf-8")
    if per_session_bad:
        (root / ".showwork/claims").mkdir()
        (root / ".showwork/claims/other.jsonl").write_text(BAD)
    (root / "check.py").write_text(script, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "historical baseline")
    baseline = git(root, "rev-parse", "HEAD")
    start_session(root, "current")
    record_requirement(root, "current", "test", "run the project check", "behavior",
                       {"type": "command", "argv": ["python", "check.py"]})
    record_claim(root, "current", "check.py exists", {"type": "file_exists", "path": "check.py"})
    assert finish_session(root, "current")[0] == 0
    git(root, "add", ".")
    git(root, "commit", "-m", "current receipt")
    return baseline


def test_default_gate_still_refuses_historical_corruption(tmp_path):
    project(tmp_path)
    assert release_gate(tmp_path, "current", require_tracked=True)["verdict"] == "RED"


def test_explicit_baseline_keeps_historical_red_visible(tmp_path):
    baseline = project(tmp_path)
    before = (tmp_path / LEGACY).read_bytes()
    result = release_gate(tmp_path, "current", require_tracked=True,
                          legacy_integrity_baseline=baseline)
    assert result["verdict"] == "GREEN"
    assert result["historical_integrity"] == "RED"
    assert result["legacy_baseline"]["commit"] == baseline
    assert result["legacy_baseline"]["acknowledged"][0]["path"] == LEGACY
    assert result["legacy_baseline"]["acknowledged"][0]["verdict"] == "RED"
    assert audit_root(tmp_path)["verdict"] == "RED"
    assert (tmp_path / LEGACY).read_bytes() == before


@pytest.mark.parametrize("mutation", ["edit", "delete", "rename", "replace_with_valid_chain"])
def test_baseline_cannot_hide_changed_or_removed_history(tmp_path, mutation):
    baseline = project(tmp_path)
    path = tmp_path / LEGACY
    if mutation == "edit":
        path.write_text(BAD.replace("historical", "rewritten"))
    elif mutation == "delete":
        path.unlink()
    elif mutation == "rename":
        path.rename(path.with_name("claims-2026-01-02.jsonl"))
    else:
        # Even rewriting the history into syntactically acceptable pre-chain
        # records must not restore integrity or satisfy the immutable baseline.
        path.write_text('{"session":"old","claim":"new history"}\n')
    result = release_gate(tmp_path, "current", legacy_integrity_baseline=baseline)
    assert result["verdict"] == "RED"
    assert any("baseline file" in error for error in result["errors"])


def test_baseline_freezes_unchained_history_too(tmp_path):
    baseline = project(tmp_path, legacy='{"session":"old","claim":"before"}\n')
    (tmp_path / LEGACY).write_text('{"session":"old","claim":"after"}\n')
    assert release_gate(tmp_path, "current", legacy_integrity_baseline=baseline)["verdict"] == "RED"


@pytest.mark.parametrize("change", ["edit", "delete", "symlink_mode"])
def test_restored_working_copy_cannot_hide_changed_head(tmp_path, change):
    # REGRESSION: restoring baseline bytes locally hid a different released HEAD.
    baseline = project(tmp_path)
    path = tmp_path / LEGACY
    if change == "edit":
        path.write_text(BAD.replace("historical", "changed in commit"))
        git(tmp_path, "add", LEGACY)
    elif change == "delete":
        git(tmp_path, "rm", LEGACY)
    else:
        blob = git(tmp_path, "rev-parse", f"HEAD:{LEGACY}")
        git(tmp_path, "update-index", "--cacheinfo", f"120000,{blob},{LEGACY}")
    git(tmp_path, "commit", "-m", "changed history")
    path.write_text(BAD)
    result = release_gate(tmp_path, "current", require_tracked=True,
                          legacy_integrity_baseline=baseline)
    assert result["verdict"] == "RED"
    assert any("HEAD" in error for error in result["errors"])


def test_baseline_refuses_new_broken_legacy_file(tmp_path):
    baseline = project(tmp_path)
    (tmp_path / ".showwork/claims-2026-02-02.jsonl").write_text(BAD)
    assert release_gate(tmp_path, "current", legacy_integrity_baseline=baseline)["verdict"] == "RED"


@pytest.mark.parametrize("already_in_baseline", [False, True])
def test_baseline_never_excuses_per_session_corruption(tmp_path, already_in_baseline):
    baseline = project(tmp_path, per_session_bad=already_in_baseline)
    if not already_in_baseline:
        (tmp_path / ".showwork/claims/other.jsonl").write_text(BAD)
    assert release_gate(tmp_path, "current", legacy_integrity_baseline=baseline)["verdict"] == "RED"


def test_baseline_cannot_include_selected_session(tmp_path):
    baseline = project(tmp_path)
    head = git(tmp_path, "rev-parse", "HEAD")
    git(tmp_path, "commit", "--allow-empty", "-m", "later")
    result = release_gate(tmp_path, "current", legacy_integrity_baseline=head)
    assert result["verdict"] == "RED"
    assert any("predate the selected session" in error for error in result["errors"])


@pytest.mark.parametrize("revision", ["HEAD", "HEAD~1", "0" * 40])
def test_baseline_requires_existing_full_commit_id(tmp_path, revision):
    project(tmp_path)
    assert release_gate(tmp_path, "current", legacy_integrity_baseline=revision)["verdict"] == "RED"


def test_baseline_rejects_unrelated_commit(tmp_path):
    project(tmp_path)
    unrelated = git(tmp_path, "commit-tree", "HEAD^{tree}", input="not an ancestor\n")
    assert release_gate(tmp_path, "current", legacy_integrity_baseline=unrelated)["verdict"] == "RED"


def test_baseline_accepts_git_crlf_checkout_conversion(tmp_path):
    baseline = project(tmp_path)
    (tmp_path / LEGACY).write_bytes(BAD.encode().replace(b"\n", b"\r\n"))
    assert release_gate(tmp_path, "current", require_tracked=True,
                        legacy_integrity_baseline=baseline)["verdict"] == "GREEN"


def test_acceptance_command_cannot_corrupt_ledger_after_audit(tmp_path):
    # REGRESSION: the gate audited before commands, so a command could add a
    # broken unrelated receipt after that audit and still return GREEN.
    script = ('from pathlib import Path\n'
              'if Path("trigger").exists():\n'
              f'    Path("{LEGACY}").write_text({BAD!r})\n')
    project(tmp_path, legacy=None, script=script)
    (tmp_path / "trigger").touch()
    result = release_gate(tmp_path, "current")
    assert result["verdict"] == "RED"
    assert result["historical_integrity"] == "RED"


def test_baseline_is_checked_after_acceptance_commands(tmp_path):
    script = ('from pathlib import Path\n'
              'if Path("trigger").exists():\n'
              f'    Path("{LEGACY}").write_text({BAD.replace("historical", "rewritten")!r})\n')
    baseline = project(tmp_path, script=script)
    (tmp_path / "trigger").touch()
    assert release_gate(tmp_path, "current", legacy_integrity_baseline=baseline)["verdict"] == "RED"


def test_cli_names_acknowledged_red_files(tmp_path, capsys):
    baseline = project(tmp_path)
    assert main(["--root", str(tmp_path), "gate", "--session", "current",
                 "--require-tracked", "--legacy-integrity-baseline", baseline]) == 0
    output = capsys.readouterr().out
    assert "historical integrity RED" in output
    assert LEGACY in output
    assert baseline in output


def test_init_workflow_uses_installed_release(tmp_path):
    # REGRESSION: the 0.6.1 package emitted an action pin that missed its fix.
    from showwork import __version__
    assert main(["--root", str(tmp_path), "init"]) == 0
    workflow = (tmp_path / "docs/ci/showwork-verify.yml").read_text()
    assert f"bmdhodl/showwork/actions/verify@v{__version__}" in workflow
