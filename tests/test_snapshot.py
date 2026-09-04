"""Undeclared deletes and edits after session.start fail verify (issue #64)."""

from __future__ import annotations

import json

from showwork.cli import main
from showwork.ledger import (
    has_minimum_proof,
    record_claim,
    session_artifacts_dir,
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


def test_unreferenced_artifact_warns_but_does_not_refuse(tmp_path):
    """A log no claim cites still ships in the PR. Verify names it."""
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    start_session(tmp_path, "art")
    arts = session_artifacts_dir(tmp_path, "art")
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "full-build.txt").write_text("800 lines of noise", encoding="utf-8")
    record_claim(
        tmp_path, "art", "keep exists",
        check={"type": "file_exists", "path": "keep.txt"},
    )
    state = verify_session(tmp_path, "art")
    assert state["verdict"] == "YELLOW"
    rows = [r for r in state["results"] if r["type"] == "unreferenced_artifact"]
    assert len(rows) == 1
    assert "full-build.txt" in rows[0]["claim"]
    # YELLOW warns. Only RED refuses a clean close.
    assert main(["--root", str(tmp_path), "finish", "--session", "art"]) == 0


def test_cited_artifact_does_not_warn(tmp_path):
    """The summary-line receipt a claim points at is proof, not clutter."""
    start_session(tmp_path, "cited")
    arts = session_artifacts_dir(tmp_path, "cited")
    arts.mkdir(parents=True, exist_ok=True)
    receipt = arts / "check-summary.txt"
    receipt.write_text("Tests 2117 passed", encoding="utf-8")
    record_claim(
        tmp_path, "cited", "the suite passed 2117 tests",
        check={
            "type": "file_contains",
            "path": receipt.relative_to(tmp_path).as_posix(),
            "pattern": "2117 passed",
        },
    )
    state = verify_session(tmp_path, "cited")
    assert state["verdict"] == "GREEN"
    assert not any(r["type"] == "unreferenced_artifact" for r in state["results"])
def test_unreferenced_artifact_alone_is_not_minimum_proof(tmp_path):
    """A synthetic row must never let a claimless session close clean."""
    assert main(["--root", str(tmp_path), "start", "--session", "bare"]) == 0
    arts = session_artifacts_dir(tmp_path, "bare")
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "stray.txt").write_text("noise", encoding="utf-8")
    state = verify_session(tmp_path, "bare")
    assert any(r["type"] == "unreferenced_artifact" for r in state["results"])
    assert has_minimum_proof(state) is False
    assert main(["--root", str(tmp_path), "finish", "--session", "bare"]) == 2
    assert _events(tmp_path, "bare")[-1]["refuse_reason"] == "no_check_backed_claims"


def test_escaping_artifacts_path_does_not_skip_the_undeclared_gate(tmp_path, monkeypatch):
    """An artifacts path outside the ledger must not buy a GREEN on a damaged tree."""
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    (tmp_path / "other.txt").write_text("y", encoding="utf-8")
    start_session(tmp_path, "escape")
    record_claim(
        tmp_path, "escape", "keep exists",
        check={"type": "file_exists", "path": "keep.txt"},
    )
    (tmp_path / "other.txt").unlink()

    def boom(root, session):
        raise ValueError("session artifacts path escapes ledger dir: 'escape'")

    monkeypatch.setattr("showwork.ledger.session_artifacts_dir", boom)
    state = verify_session(tmp_path, "escape")
    assert state["verdict"] == "RED"
    assert any(r["type"] == "undeclared_change"
               and "other.txt" in r["claim"] for r in state["results"])
    assert any("escapes the ledger" in r["claim"] for r in state["results"])


def test_generated_output_is_never_an_undeclared_change(tmp_path):
    """A build or a browser run after session.start must not turn the
    session RED: nothing under .next/ or test-results/ is something a
    person wrote, so nothing there needs a claim."""
    (tmp_path / "src.txt").write_text("real work", encoding="utf-8")
    start_session(tmp_path, "build-after-start")
    for rel in (".next/static/chunks/app.js", ".next/trace",
                "test-results/run-1/video.webm", "playwright-report/index.html",
                "coverage/lcov.info"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    record_claim(
        tmp_path, "build-after-start", "src.txt still says real work",
        check={"type": "file_contains", "path": "src.txt", "pattern": "real work"},
    )
    state = verify_session(tmp_path, "build-after-start")
    assert state["verdict"] == "GREEN"
    assert all(r["type"] != "undeclared_change" for r in state["results"])
    assert not any(k.startswith((".next/", "test-results/", "playwright-report/", "coverage/"))
                   for k in capture_tree(tmp_path))


def test_baseline_from_an_older_tool_is_judged_by_todays_skip_list(tmp_path, monkeypatch):
    """A snapshot written before .next joined SKIP_DIRS lists its files. When
    the build later rewrites or removes them, that is not an undeclared
    deletion: the baseline is filtered by the same rule as the current tree."""
    from showwork import snapshot as snap

    (tmp_path / "src.txt").write_text("real work", encoding="utf-8")
    stale = tmp_path / ".next" / "trace"
    stale.parent.mkdir(parents=True)
    stale.write_text("old build", encoding="utf-8")

    older_rule = frozenset(snap.SKIP_DIRS - {".next"})
    monkeypatch.setattr(snap, "SKIP_DIRS", older_rule)
    start_session(tmp_path, "older-baseline")
    monkeypatch.undo()
    events = _events(tmp_path, "older-baseline")
    assert events[0]["tree_snapshot"]["count"] == 2  # the old tool saw .next/trace

    stale.unlink()  # the next build sweeps it away
    record_claim(
        tmp_path, "older-baseline", "src.txt still says real work",
        check={"type": "file_contains", "path": "src.txt", "pattern": "real work"},
    )
    state = verify_session(tmp_path, "older-baseline")
    assert state["verdict"] == "GREEN", [r["claim"] for r in state["results"]]
    assert all(r["type"] != "undeclared_change" for r in state["results"])
