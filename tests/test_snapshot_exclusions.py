"""REGRESSION: opt-in background paths have a frozen, disclosed scope."""

import json
import subprocess
from pathlib import Path

import pytest

from showwork.cli import main
from showwork.ledger import finish_session, record_claim, start_session, verify_session
from showwork.outcomes import record_requirement
from showwork.reader import inspect_session


def seed(root):
    (root / "data.json").write_text("before", encoding="utf-8")
    (root / "source.py").write_text("before", encoding="utf-8")
    (root / "runs").mkdir()
    (root / "runs/events.jsonl").write_text("before", encoding="utf-8")
    (root / "anchor.txt").write_text("proof", encoding="utf-8")


def proof(root, session="scope"):
    record_requirement(root, session, "anchor", "anchor exists", "artifact",
                       {"type": "file_exists", "path": "anchor.txt"})
    record_claim(root, session, "anchor exists",
                 {"type": "file_exists", "path": "anchor.txt"})


def sidecar(root):
    return root / ".showwork/snapshots/scope.json"


def test_background_exclusions_keep_real_source_damage_red(tmp_path):
    seed(tmp_path)
    event = start_session(tmp_path, "scope", ignore=["runs/**", "data.json"])
    assert event["tree_snapshot"]["ignore_patterns"] == ["data.json", "runs/**"]
    assert event["required_semantics"] == ["snapshot-exclusions-v1"]
    proof(tmp_path)
    (tmp_path / "data.json").write_text("dashboard changed", encoding="utf-8")
    (tmp_path / "runs/events.jsonl").unlink()
    state = verify_session(tmp_path, "scope")
    assert state["verdict"] == "GREEN"
    assert state["snapshot_scope"]["ignore_patterns"] == ["data.json", "runs/**"]
    (tmp_path / "source.py").write_text("damage", encoding="utf-8")
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"
    assert finish_session(tmp_path, "scope")[0] == 2


def test_reopen_preserves_scope_and_rejects_changes_before_writes(tmp_path):
    seed(tmp_path)
    start_session(tmp_path, "scope", ignore=["data.json", "runs/**"])
    initial = sidecar(tmp_path).read_bytes()
    event = start_session(tmp_path, "scope")
    assert event["tree_snapshot"]["ignore_patterns"] == ["data.json", "runs/**"]
    start_session(tmp_path, "scope", ignore=["runs/**", "data.json", "data.json"])
    events = tmp_path / ".showwork/sessions/scope.jsonl"
    before = events.read_bytes()
    for ignore in ([], ["source.py"], ["data.json"]):
        with pytest.raises(ValueError, match="new session"):
            start_session(tmp_path, "scope", ignore=ignore)
        assert events.read_bytes() == before
        assert sidecar(tmp_path).read_bytes() == initial


@pytest.mark.parametrize("pattern", ["", "/abs", "C:/abs", "../data", "a/../b",
    ".git/config", ".showwork/**", "a/.git/x", "*", "**", "*/**", "a/**/b",
    "a/***", "a/[ab]", "a\\b", "a//b", "./data", "a/", "a\x00b", "x" * 241])
def test_invalid_patterns_reject_before_any_ledger_write(tmp_path, pattern):
    with pytest.raises(ValueError):
        start_session(tmp_path, "scope", ignore=[pattern])
    assert not (tmp_path / ".showwork").exists()


def test_pattern_count_and_type_are_bounded(tmp_path):
    for patterns in ([f"file{i}" for i in range(33)], "data.json", [None]):
        with pytest.raises(ValueError):
            start_session(tmp_path, "scope", ignore=patterns)
    assert not (tmp_path / ".showwork").exists()


def test_component_globs_are_case_sensitive_and_do_not_cross_slashes(tmp_path):
    from showwork.snapshot import capture_tree, ignored_path
    seed(tmp_path)
    # Windows cannot store both data.json and Data.json in the same directory.
    assert not ignored_path("Data.json", ["d?ta.json"])
    (tmp_path / "Case.JSON").write_text("case control", encoding="utf-8")
    (tmp_path / "runs/nested").mkdir()
    (tmp_path / "runs/nested/events.jsonl").write_text("nested", encoding="utf-8")
    captured = capture_tree(tmp_path, ignore=["d?ta.json", "runs/*.jsonl"])
    assert "data.json" not in captured and "runs/events.jsonl" not in captured
    assert "Case.JSON" in captured and "runs/nested/events.jsonl" in captured
    recursive = capture_tree(tmp_path, ignore=["runs/**"])
    assert not any(path.startswith("runs/") for path in recursive)
    assert "source.py" in recursive


@pytest.mark.parametrize("mutation", ["patterns", "format", "missing", "count", "files", "removed"])
def test_tampered_scope_refuses_and_readers_do_not_verify(tmp_path, mutation):
    seed(tmp_path)
    start_session(tmp_path, "scope", ignore=["data.json"])
    proof(tmp_path)
    assert finish_session(tmp_path, "scope")[0] == 0
    assert inspect_session(tmp_path, "scope")["recorded_outcome"] == "VERIFIED"
    payload = json.loads(sidecar(tmp_path).read_text(encoding="utf-8"))
    if mutation == "removed":
        sidecar(tmp_path).unlink()
    else:
        if mutation == "patterns":
            payload["ignore_patterns"] = ["source.py"]
        elif mutation == "format":
            payload["ignore_format"] = "unknown"
        elif mutation == "missing":
            del payload["ignore_patterns"]
        elif mutation == "count":
            payload["count"] += 1
        else:
            payload["files"]["source.py"] = "0" * 64
        sidecar(tmp_path).write_text(json.dumps(payload), encoding="utf-8")
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"
    assert finish_session(tmp_path, "scope")[0] == 2
    assert inspect_session(tmp_path, "scope")["recorded_outcome"] == "UNVERIFIED"


def test_legacy_snapshot_format_and_new_file_limit_stay_explicit(tmp_path):
    seed(tmp_path)
    event = start_session(tmp_path, "scope")
    assert set(event["tree_snapshot"]) == {"count", "sha256"}
    assert "required_semantics" not in event
    proof(tmp_path)
    (tmp_path / "brand-new.txt").write_text("outside prior-file damage guard", encoding="utf-8")
    assert finish_session(tmp_path, "scope")[0] == 0
    with pytest.raises(ValueError, match="new session"):
        start_session(tmp_path, "scope", ignore=["source.py"])


def command_session(root, code):
    seed(root)
    script = root / "check.py"
    script.write_text(code, encoding="utf-8")
    start_session(root, "scope", ignore=["data.json", "runs/**"])
    record_requirement(root, "scope", "command", "command succeeds within frozen source scope",
                       "behavior", {"type": "command", "argv": ["python", "check.py"], "expect_exit": 0})
    record_claim(root, "scope", "anchor exists", {"type": "file_exists", "path": "anchor.txt"})


def test_command_evidence_uses_frozen_exclusions(tmp_path):
    command_session(tmp_path, "from pathlib import Path\nPath('data.json').write_text('background')\n")
    state = verify_session(tmp_path, "scope")
    assert state["verdict"] == "GREEN"
    evidence = next(row["evidence"] for row in state["results"] if "requirement_id" in row)
    assert evidence["source_exclusions"]["ignore_patterns"] == ["data.json", "runs/**"]
    assert evidence["source_files"] == 3


def test_unexcluded_change_during_command_still_fails(tmp_path):
    command_session(tmp_path, "from pathlib import Path\nPath('source.py').write_text('damage')\n")
    state = verify_session(tmp_path, "scope")
    assert state["verdict"] == "RED"
    assert any("source tree changed" in row["detail"] for row in state["results"])


def test_tampered_scope_blocks_command_before_execution(tmp_path):
    command_session(tmp_path, "from pathlib import Path\nPath('ran.txt').write_text('ran')\n")
    payload = json.loads(sidecar(tmp_path).read_text(encoding="utf-8"))
    payload["ignore_patterns"] = ["source.py"]
    sidecar(tmp_path).write_text(json.dumps(payload), encoding="utf-8")
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"
    assert not (tmp_path / "ran.txt").exists()


def test_cli_accepts_repeatable_ignore_and_reports_rejected_scope(tmp_path, capsys):
    seed(tmp_path)
    args = ["--root", str(tmp_path), "start", "--session", "scope"]
    assert main([*args, "--ignore", "data.json", "--ignore", "runs/**"]) == 0
    assert main([*args, "--ignore", "source.py"]) == 2
    assert "new session" in capsys.readouterr().err


def test_python_and_js_readers_disclose_and_validate_same_scope(tmp_path, monkeypatch):
    seed(tmp_path)
    # Non-ASCII paths exercise the portable canonical JSON digest.
    (tmp_path / "é.txt").write_text("utf8", encoding="utf-8")
    (tmp_path / "😀.txt").write_text("unicode ordering", encoding="utf-8")
    start_session(tmp_path, "scope", ignore=["data.json", "runs/**"])
    proof(tmp_path)
    assert finish_session(tmp_path, "scope")[0] == 0
    reader = (Path(__file__).resolve().parents[1] / "js/showwork-audit/reader.mjs").as_uri()
    def js_read():
        code = f"import {{inspectSession}} from {json.dumps(reader)}; console.log(JSON.stringify(inspectSession(process.argv[1], 'scope')));"
        proc = subprocess.run(["node", "--input-type=module", "-e", code, str(tmp_path)],
                              capture_output=True, text=True, check=True,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return json.loads(proc.stdout)
    python = inspect_session(tmp_path, "scope")
    js = js_read()
    assert python["recorded_outcome"] == js["recorded_outcome"] == "VERIFIED"
    assert python["snapshot_scope"] == js["snapshot_scope"]
    payload = json.loads(sidecar(tmp_path).read_text(encoding="utf-8"))
    payload["ignore_patterns"].append("source.py")
    sidecar(tmp_path).write_text(json.dumps(payload), encoding="utf-8")
    assert inspect_session(tmp_path, "scope")["recorded_outcome"] == js_read()["recorded_outcome"] == "UNVERIFIED"
    def forbidden(*args, **kwargs):
        raise AssertionError("reader executed a process")
    monkeypatch.setattr(subprocess, "run", forbidden)
    assert inspect_session(tmp_path, "scope")["recorded_outcome"] == "UNVERIFIED"


def test_exclusion_does_not_suppress_an_explicit_check(tmp_path):
    seed(tmp_path)
    start_session(tmp_path, "scope", ignore=["data.json"])
    record_requirement(tmp_path, "scope", "data", "data retains its expected content", "artifact",
                       {"type": "file_contains", "path": "data.json", "pattern": "before"})
    record_claim(tmp_path, "scope", "anchor exists", {"type": "file_exists", "path": "anchor.txt"})
    (tmp_path / "data.json").write_text("wrong", encoding="utf-8")
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"


def test_command_cache_ignores_background_bytes_but_binds_scope(tmp_path):
    from showwork.checks import verify_claim
    seed(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/run_tests.py").write_text("print('passed')\n", encoding="utf-8")
    start_session(tmp_path, "scope", ignore=["data.json", "runs/**"])
    start_session(tmp_path, "other", ignore=["data.json", "runs/**", "absent.txt"])
    cache = {}
    record = {"session": "scope", "claim": "test", "check": {"type": "command",
              "argv": ["python", "scripts/run_tests.py"], "expect_exit": 0}}
    first = verify_claim(record, tmp_path, command_cache=cache)
    assert first["status"] == "pass"
    (tmp_path / "data.json").write_text("background change", encoding="utf-8")
    again = verify_claim(record, tmp_path, command_cache=cache)
    assert again["status"] == "pass" and again["evidence"]["execution_reused"]
    other = verify_claim({**record, "session": "other"}, tmp_path, command_cache=cache)
    assert other["status"] == "pass" and not other["evidence"]["execution_reused"]
    assert first["evidence"]["source_sha256"] != other["evidence"]["source_sha256"]


def test_appended_start_cannot_weaken_original_scope(tmp_path):
    from showwork.ledger import record_event
    command_session(tmp_path, "from pathlib import Path\nPath('ran.txt').write_text('ran')\n")
    meta = json.loads(sidecar(tmp_path).read_text(encoding="utf-8"))
    record_event(tmp_path, "session.start", "scope", tree_snapshot={
        "count": meta["count"], "sha256": meta["sha256"],
        "ignore_format": meta["ignore_format"], "ignore_patterns": ["source.py"]},
        required_semantics=["snapshot-exclusions-v1"])
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"
    assert not (tmp_path / "ran.txt").exists()
    assert inspect_session(tmp_path, "scope")["recorded_outcome"] == "UNVERIFIED"


def test_duplicate_sidecar_key_is_refused(tmp_path):
    seed(tmp_path)
    start_session(tmp_path, "scope", ignore=["data.json"])
    proof(tmp_path)
    text = sidecar(tmp_path).read_text(encoding="utf-8")
    sidecar(tmp_path).write_text(text.rstrip()[:-1] + ',"ignore_patterns":["data.json"]}', encoding="utf-8")
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"
    assert inspect_session(tmp_path, "scope")["recorded_outcome"] == "UNVERIFIED"


@pytest.mark.parametrize("missing", ["sha256", "count", "ignore_patterns", "ignore_format"])
def test_missing_chained_metadata_cannot_qualify(tmp_path, missing):
    from showwork.ledger import record_event, _latest_session_start
    seed(tmp_path)
    start_session(tmp_path, "scope", ignore=["data.json"])
    proof(tmp_path)
    meta = dict(_latest_session_start(tmp_path, "scope")["tree_snapshot"])
    del meta[missing]
    record_event(tmp_path, "session.start", "scope", tree_snapshot=meta,
                 required_semantics=["snapshot-exclusions-v1"])
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"
    assert inspect_session(tmp_path, "scope")["recorded_outcome"] == "UNVERIFIED"


def test_gitignore_never_weakens_snapshot_scope(tmp_path):
    seed(tmp_path)
    (tmp_path / ".gitignore").write_text("data.json\n", encoding="utf-8")
    start_session(tmp_path, "scope", ignore=["runs/**"])
    proof(tmp_path)
    (tmp_path / "data.json").write_text("gitignored damage", encoding="utf-8")
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"


@pytest.mark.parametrize("semantics", [True, 42, "snapshot-exclusions-v1", {"snapshot-exclusions-v1": True}])
def test_malformed_exclusion_capability_fails_visibly(tmp_path, semantics):
    from showwork.ledger import record_event, _latest_session_start
    seed(tmp_path)
    start_session(tmp_path, "scope", ignore=["data.json"])
    proof(tmp_path)
    meta = _latest_session_start(tmp_path, "scope")["tree_snapshot"]
    record_event(tmp_path, "session.start", "scope", tree_snapshot=meta, required_semantics=semantics)
    assert verify_session(tmp_path, "scope")["verdict"] == "RED"
    assert inspect_session(tmp_path, "scope")["recorded_outcome"] == "UNVERIFIED"
