"""showwork init writes Cursor, Claude, and CI glue without touching .github/."""

from __future__ import annotations

import json

from showwork.cli import main
from showwork.scaffold import init_project


def test_init_writes_cursor_claude_and_docs_ci(tmp_path):
    notes = init_project(tmp_path)
    joined = "\n".join(notes)
    assert "write .cursor/rules/showwork.mdc" in joined
    assert "write .claude/settings.json" in joined
    assert "write docs/ci/showwork-verify.yml" in joined
    rule = (tmp_path / ".cursor" / "rules" / "showwork.mdc").read_text(encoding="utf-8")
    assert "python -m showwork finish" in rule
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "python -m showwork stop-hook" in json.dumps(settings)
    ci = (tmp_path / "docs" / "ci" / "showwork-verify.yml").read_text(encoding="utf-8")
    assert "bmdhodl/showwork/actions/verify@" in ci
    assert not (tmp_path / ".github").exists()


def test_init_merges_existing_claude_settings(tmp_path):
    dest = tmp_path / ".claude" / "settings.json"
    dest.parent.mkdir(parents=True)
    dest.write_text(json.dumps({"permissions": {"allow": ["Bash"]}}), encoding="utf-8")
    notes = init_project(tmp_path, cursor=False, ci=False)
    assert notes[0].startswith("merge ")
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["permissions"]["allow"] == ["Bash"]
    assert "Stop" in data["hooks"]


def test_init_skips_existing_cursor_rule_without_force(tmp_path):
    dest = tmp_path / ".cursor" / "rules" / "showwork.mdc"
    dest.parent.mkdir(parents=True)
    dest.write_text("keep me\n", encoding="utf-8")
    notes = init_project(tmp_path, claude=False, ci=False)
    assert "skip " in notes[0]
    assert dest.read_text(encoding="utf-8") == "keep me\n"
    init_project(tmp_path, cursor=True, claude=False, ci=False, force=True)
    assert "keep me" not in dest.read_text(encoding="utf-8")


def test_cli_init(tmp_path):
    code = main(["--root", str(tmp_path), "init", "--cursor"])
    assert code == 0
    assert (tmp_path / ".cursor" / "rules" / "showwork.mdc").is_file()
    assert not (tmp_path / ".claude" / "settings.json").exists()
