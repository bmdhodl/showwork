"""Public tree must not ship owner machine paths or host names."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git", ".venv", ".showwork", "tests", ".claude", "__pycache__",
    ".pytest_cache", "node_modules",
}
NEEDLES = (
    "Users\\patri",
    "Users/patri",
    "fluarmn",
    "OneOncology",
    "K:\\autotrader",
    "K:/autotrader",
)
SUFFIXES = {".md", ".json", ".yml", ".yaml", ".py", ".toml", ".txt", ".mjs"}


def test_public_tree_has_no_private_owner_paths():
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for needle in NEEDLES:
            if needle in text:
                rel = path.relative_to(ROOT).as_posix()
                hits.append(f"{rel}: {needle}")
    assert hits == [], "private owner paths in public tree:\n" + "\n".join(hits)
