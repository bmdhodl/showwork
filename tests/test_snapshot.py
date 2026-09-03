"""Undeclared deletes and edits after session.start fail verify (issue #64)."""

from __future__ import annotations

import json

from showwork.cli import main
from showwork.ledger import (
    record_claim,
    start_session,
    verify_session,
)
from showwork.snapshot import capture_tree, declared_paths


def _events(root, session):
    path = root / ".showwork" / "sessions" / f"{session}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def test_start_records_tree_snapshot(tmp_path):
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    rec = start_session(tmp_path, "snap")
    meta = rec["tree_snapshot"]
    assert meta["count"] == 1
    assert len(meta["sha256"]) == 64
    sidecar = tmp_path / ".showwork" / "snapshots" / "snap.json"
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["sha256"] == meta["sha256"]
    assert payload["files"]["keep.txt"]


def test_undeclared_delete_is_red(tmp_path):
    src = tmp_path / "src.txt"
    other = tmp_path / "other.txt"
    src.write_text("move me", encoding="utf-8")
    other.write_text("do not touch", encoding="utf-8")
    start_session(tmp_path, "issue-64")
    dst = tmp_path / "dst.txt"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    src.unlink()
    record_claim(
        tmp_path, "issue-64", "moved src to dst",
        check={"type": "path_moved", "from": "src.txt", "to": "dst.txt"},
    )
    other.unlink()
    state = verify_session(tmp_path, "issue-64")
    assert state["verdict"] == "RED"
    kinds = {r["type"] for r in state["results"]}
    assert "path_moved" in kinds
    assert "undeclared_change" in kinds
    details = " ".join(r["detail"] for r in state["results"] if r["type"] == "undeclared_change")
    assert "other.txt" in details


def test_undeclared_edit_is_red(tmp_path):
    (tmp_path / "secret.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "named.txt").write_text("ok", encoding="utf-8")
    start_session(tmp_path, "edit")
    (tmp_path / "secret.txt").write_text("changed", encoding="utf-8")
    record_claim(
        tmp_path, "edit", "named exists",
        check={"type": "file_exists", "path": "named.txt"},
    )
    state = verify_session(tmp_path, "edit")
    assert state["verdict"] == "RED"
    assert any("secret.txt" in r["claim"] for r in state["results"]
               if r["type"] == "undeclared_change")


def test_declared_path_may_change(tmp_path):
    (tmp_path / "named.txt").write_text("before", encoding="utf-8")
    start_session(tmp_path, "declared")
    (tmp_path / "named.txt").write_text("after", encoding="utf-8")
    record_claim(
        tmp_path, "declared", "named contains after",
        check={"type": "file_contains", "path": "named.txt", "pattern": "after"},
    )
    state = verify_session(tmp_path, "declared")
    assert state["verdict"] == "GREEN"
    assert all(r["type"] != "undeclared_change" for r in state["results"])


def test_legacy_session_without_snapshot_skips(tmp_path):
    (tmp_path / "gone.txt").write_text("x", encoding="utf-8")
    sessions = tmp_path / ".showwork" / "sessions"
    claims = tmp_path / ".showwork" / "claims"
    sessions.mkdir(parents=True)
    claims.mkdir(parents=True)
    start = {"event": "session.start", "session": "legacy", "ts": "2026-08-01T00:00:00"}
    claim = {
        "session": "legacy", "ts": "2026-08-01T00:00:01",
        "claim": "named", "severity": "RED",
        "check": {"type": "file_exists", "path": "gone.txt"},
    }
    (sessions / "legacy.jsonl").write_text(json.dumps(start) + "\n", encoding="utf-8")
    (claims / "legacy.jsonl").write_text(json.dumps(claim) + "\n", encoding="utf-8")
    (tmp_path / "gone.txt").unlink()
    # Claim fails because the file is gone; undeclared check must not also run.
    state = verify_session(tmp_path, "legacy")
    assert all(r.get("type") != "undeclared_change" for r in state["results"])
    assert state["verdict"] == "RED"


def test_missing_snapshot_is_red(tmp_path):
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    start_session(tmp_path, "tamper")
    record_claim(
        tmp_path, "tamper", "keep exists",
        check={"type": "file_exists", "path": "keep.txt"},
    )
    snap = tmp_path / ".showwork" / "snapshots" / "tamper.json"
    snap.unlink()
    state = verify_session(tmp_path, "tamper")
    assert state["verdict"] == "RED"
    assert any(r["type"] == "undeclared_change" for r in state["results"])


def test_new_unclaimed_file_is_not_undeclared_damage(tmp_path):
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    start_session(tmp_path, "newfile")
    (tmp_path / "scratch.log").write_text("noise", encoding="utf-8")
    record_claim(
        tmp_path, "newfile", "keep exists",
        check={"type": "file_exists", "path": "keep.txt"},
    )
    state = verify_session(tmp_path, "newfile")
    assert state["verdict"] == "GREEN"


def test_finish_refuses_undeclared_delete(tmp_path):
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    (tmp_path / "other.txt").write_text("y", encoding="utf-8")
    assert main(["--root", str(tmp_path), "start", "--session", "fin"]) == 0
    assert main(["--root", str(tmp_path), "claim", "--session", "fin",
                 "--claim", "keep exists", "--type", "file_exists",
                 "--path", "keep.txt"]) == 0
    (tmp_path / "other.txt").unlink()
    assert main(["--root", str(tmp_path), "finish", "--session", "fin"]) == 2
    events = _events(tmp_path, "fin")
    assert events[-1]["event"] == "session.finish.refused"


def test_showwork_dir_is_excluded_from_snapshot(tmp_path):
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    start_session(tmp_path, "ledger")
    tree = capture_tree(tmp_path)
    assert "keep.txt" in tree
    assert not any(path.startswith(".showwork/") for path in tree)


def test_declared_paths_include_path_moved_from(tmp_path):
    claims = [{
        "session": "s", "claim": "moved", "severity": "RED",
        "check": {"type": "path_moved", "from": "a.txt", "to": "b.txt"},
    }]
    named = declared_paths(claims, tmp_path)
    assert "a.txt" in named
    assert "b.txt" in named
