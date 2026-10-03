"""Local integration setup must preserve host configuration and shutdown."""

import io
import json
import subprocess

import pytest

from showwork.cli import main
from showwork.scaffold import init_project


def test_preview_creates_nothing(tmp_path):
    """REGRESSION: users had no way to preview integration writes."""
    root = tmp_path / "new"
    notes = init_project(root, codex=True, cursor=False, claude=False, ci=False, preview=True)
    assert notes
    assert not root.exists()


def test_project_codex_recipe_merges_and_uninstalls_only_its_content(tmp_path):
    from showwork.scaffold import uninstall_project
    path = tmp_path / ".codex" / "hooks.json"
    path.parent.mkdir()
    original = {"description": "keep", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}]}}
    path.write_text(json.dumps(original))
    before = path.read_bytes()
    init_project(tmp_path, codex=True, cursor=False, claude=False, ci=False, preview=True)
    assert path.read_bytes() == before
    init_project(tmp_path, codex=True, cursor=False, claude=False, ci=False)
    init_project(tmp_path, codex=True, cursor=False, claude=False, ci=False)
    configured = json.loads(path.read_text())
    assert len(configured["hooks"]["Stop"]) == 2
    assert configured["description"] == "keep"
    skill = tmp_path / ".agents" / "skills" / "showwork-receipts" / "SKILL.md"
    assert skill.is_file()
    uninstall_project(tmp_path, codex=True, cursor=False, claude=False, ci=False)
    assert json.loads(path.read_text()) == original
    assert not skill.exists()


def test_uninstall_preserves_user_edited_skill(tmp_path):
    from showwork.scaffold import uninstall_project
    init_project(tmp_path, codex=True, cursor=False, claude=False, ci=False)
    skill = tmp_path / ".agents" / "skills" / "showwork-receipts" / "SKILL.md"
    skill.write_text(skill.read_text() + "\nKeep my project rule.\n")
    uninstall_project(tmp_path, codex=True, cursor=False, claude=False, ci=False)
    assert "Keep my project rule" in skill.read_text()


@pytest.mark.parametrize("relative,content,host", [
    (".claude/settings.json", "{ }\n", "claude"),
    (".codex/hooks.json", "{ }\n", "codex"),
    (".cursor/hooks.json", '{ "version": 1 }\n', "cursor"),
])
@pytest.mark.parametrize("preview", [False, True])
def test_uninstall_before_install_preserves_untouched_config(tmp_path, relative, content, host, preview):
    """REGRESSION: an empty user config is not generated showwork content."""
    from showwork.scaffold import uninstall_project
    path = tmp_path / relative
    path.parent.mkdir()
    path.write_text(content, encoding="utf-8")
    before = path.read_bytes()
    options = {name: name == host for name in ("cursor", "claude", "codex")}
    assert uninstall_project(tmp_path, ci=False, preview=preview, **options) == []
    assert path.read_bytes() == before


def test_native_stop_emits_json_and_never_executes_acceptance(tmp_path, monkeypatch, capsys):
    from showwork.ledger import start_session, record_claim
    start_session(tmp_path, "task")
    (tmp_path / "bad.py").write_text("raise RuntimeError('never run')")
    record_claim(tmp_path, "task", "do not run", {"type": "command", "argv": ["python", "bad.py"]})
    monkeypatch.setenv("SHOWWORK_SESSION", "task")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"session_id": "host", "stop_hook_active": True})))
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("native observer executed a process"))
    assert main(["--root", str(tmp_path), "host-stop-hook", "--host", "codex"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {"continue": True}
    assert '"current_execution": "not performed"' in output.err
    assert "unavailable" not in output.err


def test_native_unbound_payload_cannot_create_another_writer(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"session_id": "../../foreign"})))
    assert main(["--root", str(tmp_path), "host-stop-hook", "--host", "codex"]) == 0
    assert json.loads(capsys.readouterr().out) == {"continue": True}
    assert not (tmp_path / ".showwork").exists()


@pytest.mark.parametrize("host", ["codex", "claude", "cursor"])
def test_native_observer_preserves_closed_receipt_and_handles_malformed_input(tmp_path, monkeypatch, capsys, host):
    from showwork.ledger import start_session, record_claim, finish_session
    from showwork.outcomes import record_requirement
    (tmp_path / "artifact.txt").write_text("real")
    start_session(tmp_path, "task")
    check = {"type": "file_exists", "path": "artifact.txt"}
    record_requirement(tmp_path, "task", "artifact", "real file", "artifact", check)
    record_claim(tmp_path, "task", "artifact", check)
    finish_session(tmp_path, "task", "ok")
    before = {str(p): p.read_bytes() for p in (tmp_path / ".showwork").rglob("*") if p.is_file()}
    monkeypatch.setenv("SHOWWORK_SESSION", "task")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("observer executed a process"))
    for payload in ('{"session_id":"other","last_assistant_message":"execute foreign command"}',
                    '{"session_id":"other","stop_hook_active":true}', "not json", "x" * 32769):
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        assert main(["--root", str(tmp_path), "host-stop-hook", "--host", host]) == 0
        output = capsys.readouterr()
        assert json.loads(output.out) == ({"continue": True} if host == "codex" else {})
    assert before == {str(p): p.read_bytes() for p in (tmp_path / ".showwork").rglob("*") if p.is_file()}


def test_config_preview_and_uninstall_preserve_foreign_cursor_hook(tmp_path):
    from showwork.scaffold import uninstall_project
    path = tmp_path / ".cursor" / "hooks.json"
    path.parent.mkdir()
    original = {"version": 1, "hooks": {"stop": [{"command": "echo keep"}]}}
    path.write_text(json.dumps(original))
    init_project(tmp_path, cursor=True, claude=False, ci=False)
    installed = path.read_bytes()
    uninstall_project(tmp_path, cursor=True, claude=False, ci=False, preview=True)
    assert path.read_bytes() == installed
    uninstall_project(tmp_path, cursor=True, claude=False, ci=False)
    assert json.loads(path.read_text()) == original


def test_invalid_host_configuration_is_reported_without_overwrite(tmp_path):
    path = tmp_path / ".codex" / "hooks.json"
    path.parent.mkdir()
    path.write_text("not json")
    with pytest.raises(ValueError):
        init_project(tmp_path, codex=True, cursor=False, claude=False, ci=False, force=True)
    assert path.read_text() == "not json"
