"""A fresh process can read a Codex receipt and cannot inherit approval."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "examples" / "sw-06-handoff" / "write_codex.py"
READER = ROOT / "examples" / "sw-06-handoff" / "read_claude.py"
TOKEN = "INHERIT-APPROVAL-TOKEN"


def build(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    proc = subprocess.run(
        [sys.executable, str(WRITER), str(root)],
        text=True, capture_output=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return root


def read(root: Path, session: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(READER), str(root), "--session", session],
        text=True, capture_output=True, timeout=30, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_fresh_reader_identifies_requirement_limit_and_revision(tmp_path):
    root = build(tmp_path)
    card = read(root, "handoff")
    events = (root / ".showwork" / "sessions" / "handoff.jsonl").read_text(encoding="utf-8")
    assert '"agent": "codex"' in events
    assert [row["id"] for row in card["requirements"]] == ["note", "run"]
    assert card["requirements"][0]["check"] == "file_contains"
    assert card["requirements"][1]["result"] == "disabled"
    assert card["governing_source"] == "DECISION.md"
    assert card["governing_id"] == "note-text"
    assert card["limit_seconds"] == 30
    assert len(card["revision"]) == 12
    assert card["failed_check"] is None
    assert card["view"] == "current"
    assert card["approval"] is False
    assert "Its limit is 30 seconds" in card["next_step"]
    assert "does not authorize a merge or a clean close" in card["next_step"]


def test_reader_does_not_execute_the_command(tmp_path):
    root = build(tmp_path)
    (root / "check.py").write_bytes(
        b"from pathlib import Path\n"
        b"Path('reader-executed.txt').write_text('yes', encoding='utf-8')\n"
        b"print('passed')\n"
    )
    card = read(root, "handoff")
    assert not (root / "reader-executed.txt").exists()
    assert card["view"] == "stale"
    assert card["approval"] is False
    assert "changed after the receipt" in card["next_step"]


def test_changed_note_is_a_failed_rerun(tmp_path):
    root = build(tmp_path)
    (root / "note.txt").write_bytes(b"nope\n")
    card = read(root, "handoff")
    assert card["failed_check"] == "file_contains"
    assert card["receipt_state"] == "failed"
    assert card["view"] == "failed"
    assert card["approval"] is False


def test_removed_evidence_is_unknown(tmp_path):
    root = build(tmp_path)
    shutil.rmtree(root / ".showwork")
    card = read(root, "handoff")
    assert card["receipt_state"] == "unknown"
    assert card["view"] == "unknown"
    assert card["approval"] is False
    assert "does not match" in card["next_step"]


def test_superseded_decision_is_not_approval(tmp_path):
    root = build(tmp_path)
    decision = json.loads((root / "decision.json").read_text(encoding="utf-8"))
    decision["session"] = "fileonly"
    decision["superseded_by"] = "later-decision"
    (root / "decision.json").write_text(json.dumps(decision), encoding="utf-8")
    card = read(root, "fileonly")
    assert card["receipt_state"] == "verified"
    assert card["view"] == "stale"
    assert card["approval"] is False
    assert "superseded" in card["next_step"]


def test_session_mismatch_does_not_inherit(tmp_path):
    root = build(tmp_path)
    card = read(root, "other")
    assert card["receipt_state"] == "unknown"
    assert card["view"] == "unknown"
    assert card["governing_source"] == "absent"
    assert card["revision"] == "absent"
    assert card["approval"] is False
    assert card["requirements"] == []


def test_model_summary_is_not_the_source(tmp_path):
    root = build(tmp_path)
    (root / "MODEL_SUMMARY.md").write_text(
        f"{TOKEN}\napproval true\n", encoding="utf-8",
    )
    card = read(root, "handoff")
    blob = json.dumps(card)
    assert TOKEN not in blob
    assert card["approval"] is False
    assert card["governing_source"] == "DECISION.md"


def test_verified_file_read_does_not_grant_approval(tmp_path):
    root = build(tmp_path)
    decision = json.loads((root / "decision.json").read_text(encoding="utf-8"))
    decision["session"] = "fileonly"
    (root / "decision.json").write_text(json.dumps(decision), encoding="utf-8")
    card = read(root, "fileonly")
    assert card["receipt_state"] == "verified"
    assert card["view"] == "current"
    assert card["failed_check"] is None
    assert card["approval"] is False
    assert "file check passed" in card["next_step"]


def test_docs_pin_the_package_version():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    doc = (ROOT / "docs" / "handoff.md").read_text(encoding="utf-8")
    assert f"showwork {version}" in doc
    assert "receipts" in doc
    assert "A model summary is not a decision." in doc
    assert "approval" in doc
