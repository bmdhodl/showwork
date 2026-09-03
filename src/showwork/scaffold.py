"""Write Cursor, Claude, and CI glue into a project root."""

from __future__ import annotations

import json
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
    force: bool = False,
) -> list[str]:
    """Write adapter files. Returns a list of write/skip/merge notes."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    if cursor:
        dest = root / ".cursor" / "rules" / "showwork.mdc"
        notes.append(_write_text(root, dest, _template("cursor-rule.mdc"), force))
    if claude:
        notes.append(_write_claude(root, force=force))
    if ci:
        dest = root / "docs" / "ci" / "showwork-verify.yml"
        notes.append(_write_text(root, dest, _template("ci-verify.yml"), force))
    return notes


def _rel(root: Path, dest: Path) -> str:
    return dest.resolve().relative_to(root).as_posix()


def _write_text(root: Path, dest: Path, text: str, force: bool) -> str:
    rel = _rel(root, dest)
    if dest.is_file() and not force:
        return f"skip {rel} (exists; pass --force)"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return f"write {rel}"


def _write_claude(root: Path, *, force: bool) -> str:
    dest = root / ".claude" / "settings.json"
    rel = _rel(root, dest)
    incoming = json.loads(_template("claude-settings.json"))
    if dest.is_file() and not force:
        try:
            existing = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return f"skip {rel} (unreadable JSON; pass --force)"
        if not isinstance(existing, dict):
            return f"skip {rel} (settings.json is not an object; pass --force)"
        merged = _merge_claude(existing, incoming)
        dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        return f"merge {rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(incoming, indent=2) + "\n", encoding="utf-8")
    return f"write {rel}"


def _merge_claude(existing: dict, incoming: dict) -> dict:
    """Keep unknown keys. Add the Stop hook if it is not already present."""
    out = dict(existing)
    hooks = dict(out.get("hooks") or {}) if isinstance(out.get("hooks"), dict) else {}
    stop = list(hooks.get("Stop") or [])
    incoming_stop = ((incoming.get("hooks") or {}).get("Stop") or [])
    already = json.dumps(stop)
    if "python -m showwork stop-hook" not in already:
        if isinstance(incoming_stop, list):
            stop.extend(incoming_stop)
    hooks["Stop"] = stop
    out["hooks"] = hooks
    return out
