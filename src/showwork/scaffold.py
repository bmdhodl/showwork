"""Preview, install and remove project-local host recipes."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def init_project(
    root: Path,
    *,
    cursor: bool = True,
    claude: bool = True,
    ci: bool = True,
    codex: bool = False,
    force: bool = False,
    preview: bool = False,
) -> list[str]:
    """Write adapter files. Returns a list of write/skip/merge notes."""
    root = root.resolve()
    notes: list[str] = []
    if cursor:
        dest = root / ".cursor" / "rules" / "showwork.mdc"
        notes.append(_write_text(root, dest, _template("cursor-rule.mdc"), force, preview))
        notes.append(_write_config(root, ".cursor/hooks.json", "cursor-hooks.json", preview))
    if claude:
        notes.append(_write_config(root, ".claude/settings.json", "claude-settings.json", preview))
    if codex:
        notes.append(_write_config(root, ".codex/hooks.json", "codex-hooks.json", preview))
        dest = root / ".agents" / "skills" / "showwork-receipts" / "SKILL.md"
        notes.append(_write_text(root, dest, _template("codex-skill.md"), force, preview))
    if ci:
        dest = root / "docs" / "ci" / "showwork-verify.yml"
        notes.append(_write_text(root, dest, _template("ci-verify.yml"), force, preview))
    return notes


def _rel(root: Path, dest: Path) -> str:
    return dest.resolve().relative_to(root).as_posix()


def _write_text(root: Path, dest: Path, text: str, force: bool, preview: bool = False) -> str:
    rel = _rel(root, dest)
    if dest.is_file() and not force:
        return f"skip {rel} (exists; pass --force)"
    if preview:
        return f"would write {rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return f"write {rel}"


def _write_config(root: Path, relative: str, template: str, preview: bool) -> str:
    dest = root / relative
    rel = _rel(root, dest)
    incoming = json.loads(_template(template))
    existing = _read_config(dest)
    merged = _merge_claude(existing, incoming)
    for key, value in incoming.items():
        if key != "hooks" and key not in merged:
            merged[key] = value
    action = "merge" if dest.exists() else "write"
    if preview:
        return f"would {action} {rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return f"{action} {rel}"


def _read_config(dest: Path) -> dict:
    if not dest.exists():
        return {}
    existing = json.loads(dest.read_text(encoding="utf-8"))
    if not isinstance(existing, dict):
        raise ValueError(f"{dest.name} must contain a JSON object; preserve and repair it")
    hooks = existing.get("hooks", {})
    if not isinstance(hooks, dict) or any(not isinstance(items, list) for items in hooks.values()):
        raise ValueError(f"{dest.name} hooks must map event names to lists")
    return existing


def _merge_claude(existing: dict, incoming: dict) -> dict:
    """Keep unknown keys. Add the Stop hook if it is not already present."""
    out = json.loads(json.dumps(existing))
    hooks = out.get("hooks", {})
    for event, entries in incoming["hooks"].items():
        current = hooks.setdefault(event, [])
        for entry in entries:
            # Recognize both documented legacy spellings. Installing again must
            # not duplicate a hook or silently replace an edited command.
            if not any(_has_showwork_hook(item, event) for item in current):
                current.append(entry)
    out["hooks"] = hooks
    return out


def _has_showwork_hook(entry: dict, event: str) -> bool:
    if not isinstance(entry, dict):
        return False
    commands = entry.get("hooks", []) if event == "Stop" else [entry]
    return any(isinstance(item, dict) and item.get("type", "command") == "command"
               and _is_showwork_command(item.get("command"), ("stop-hook", "host-stop-hook"))
               for item in commands)


def _is_showwork_command(command: object, kinds: tuple[str, ...] = ("stop-hook",)) -> bool:
    if not isinstance(command, str):
        return False
    try:
        argv = [item.strip("\"'") for item in shlex.split(command, posix=False)]
    except ValueError:
        return False
    if not argv:
        return False
    launcher = re.split(r"[/\\]", argv[0])[-1]
    if not re.fullmatch(r"(?:python(?:\d(?:\.\d+)*)?|py)(?:\.exe)?", launcher, re.I):
        return False
    if launcher.lower() in {"py", "py.exe"} and len(argv) > 1 and re.fullmatch(r"-3(?:\.\d+)?", argv[1]):
        argv.pop(1)
    return len(argv) >= 4 and argv[1] == "-m" and argv[2] in {"showwork", "showwork.cli"} and argv[3] in kinds


def uninstall_project(root: Path, *, cursor: bool = True, claude: bool = True,
                      ci: bool = True, codex: bool = False, preview: bool = False) -> list[str]:
    """Remove only unchanged generated content; retain edits and foreign hooks."""
    root = root.resolve()
    notes = []
    files = []
    configs = []
    if cursor:
        files.append((".cursor/rules/showwork.mdc", "cursor-rule.mdc"))
        configs.append((".cursor/hooks.json", "cursor-hooks.json"))
    if claude:
        configs.append((".claude/settings.json", "claude-settings.json"))
    if codex:
        files.append((".agents/skills/showwork-receipts/SKILL.md", "codex-skill.md"))
        configs.append((".codex/hooks.json", "codex-hooks.json"))
    if ci:
        files.append(("docs/ci/showwork-verify.yml", "ci-verify.yml"))
    for relative, template in files:
        dest = root / relative
        _rel(root, dest)  # Reject escaping symlinks before reading or removing.
        if not dest.is_file():
            continue
        if dest.read_text(encoding="utf-8") != _template(template):
            notes.append(f"keep {relative} (edited)")
            continue
        notes.append(f"{'would remove' if preview else 'remove'} {relative}")
        if not preview:
            dest.unlink()
    for relative, template in configs:
        dest = root / relative
        _rel(root, dest)
        if not dest.is_file():
            continue
        existing = _read_config(dest)
        incoming = json.loads(_template(template))
        hooks = existing.get("hooks", {})
        removed = False
        for event, entries in incoming["hooks"].items():
            if event not in hooks:
                continue
            retained = [entry for entry in hooks[event] if entry not in entries]
            removed = removed or len(retained) != len(hooks[event])
            hooks[event] = retained
            if not hooks[event]:
                del hooks[event]
        if not removed:
            continue
        if not hooks:
            existing.pop("hooks", None)
        if existing == {"version": incoming.get("version")}:
            existing = {}
        notes.append(f"{'would remove generated hooks from' if preview else 'remove generated hooks from'} {relative}")
        if not preview:
            if existing:
                dest.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
            else:
                dest.unlink()
    return notes
