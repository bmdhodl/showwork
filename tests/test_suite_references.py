"""Sanitized reference fixtures; real installed SDK proof is separate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from showwork.checks import VERIFYING_ENV
from showwork.ledger import start_session, record_claim, finish_session, load_all_events, record_event
from showwork.outcomes import record_requirement

READER = Path(__file__).resolve().parents[1] / "examples/suite/read_evidence.py"
spec = importlib.util.spec_from_file_location("suite_example", READER)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).strip()


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.delenv(VERIFYING_ENV, raising=False)
    monkeypatch.delenv("SHOWWORK_NO_COMMANDS", raising=False)
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "check.py").write_text("print('passed')\n", encoding="utf-8")
    (root / "artifact.txt").write_text("ready\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "check.py", "artifact.txt")
    git(root, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "sanitized fixture")
    revision = git(root, "rev-parse", "HEAD")
    start_session(root, "case", ignore=["runtime.jsonl", "runtime-receipt.json"])
    record_requirement(root, "case", "run", "check.py passes", "behavior",
        {"type": "command", "argv": ["python", "check.py"], "expect_exit": 0,
         "stdout_contains": "passed"})
    record_requirement(root, "case", "artifact", "artifact contains ready", "artifact",
        {"type": "file_contains", "path": "artifact.txt", "pattern": "ready"})
    record_claim(root, "case", "artifact exists", check={"type": "file_exists", "path": "artifact.txt"})
    write_runtime(root)
    code, state = finish_session(root, "case", "ok")
    assert code == 0 and state["outcome"]["verdict"] == "VERIFIED"
    return root, revision


def write_runtime(root, *, stopped=False):
    raw = (json.dumps({"name": "llm.result", "data": {}, "session_id": "runtime-case"}) + "\n").encode()
    (root / "runtime.jsonl").write_bytes(raw)
    payload = {"trace": "runtime.jsonl", "sha256": hashlib.sha256(raw).hexdigest(),
               "events": 1, "llm_calls": 1, "tool_calls": 0, "recorded_cost_usd": 0,
               "budget_warnings": 0, "stops": [{"kind": "budget", "detail": "1 calls, limit 1"}] if stopped else [],
               "version": "1.4.1"}
    (root / "runtime-receipt.json").write_text(json.dumps(payload), encoding="utf-8")


def read(workspace, **kwargs):
    root, revision = workspace
    return example.read_evidence(root, "case", "run", revision, **kwargs)


def test_recorded_behavior_does_not_authorize_current_execution(workspace):
    view = read(workspace)
    assert view["runtime"]["state"] == "no_recorded_stop"
    assert view["acceptance"]["state"] == "recorded_verified"
    assert view["acceptance"]["requirement"]["scope"] == "behavior"
    assert view["acceptance"]["requirement"]["claim"] == "check.py passes"
    assert view["acceptance"]["command_evidence"]["git_commit"] == workspace[1]
    assert view["current_execution"] == "not performed"
    assert view["current_outcome"] == "UNVERIFIED"
    assert view["dispatch_authorized"] is False


def test_artifact_scope_stays_artifact_scope(workspace):
    root, revision = workspace
    view = example.read_evidence(root, "case", "artifact", revision)
    assert view["acceptance"]["state"] == "recorded_verified"
    assert view["acceptance"]["requirement"]["scope"] == "artifact"
    assert view["current_execution"] == "not performed"


@pytest.mark.parametrize("change", ["missing", "tampered", "wrong_version", "malformed", "escaping"])
def test_bad_runtime_reference_never_becomes_permission(workspace, change):
    root, _ = workspace
    args = {}
    if change == "missing":
        (root / "runtime.jsonl").unlink()
    elif change == "tampered":
        (root / "runtime.jsonl").write_text("{}\n", encoding="utf-8")
    elif change == "wrong_version":
        payload = json.loads((root / "runtime-receipt.json").read_text())
        payload["version"] = "999.0"
        (root / "runtime-receipt.json").write_text(json.dumps(payload))
    elif change == "malformed":
        (root / "runtime-receipt.json").write_text("[]")
    else:
        args["trace"] = "../runtime.jsonl"
    view = read(workspace, **args)
    assert view["runtime"]["state"] == "unknown"
    assert view["reference_status"] == "unknown"
    assert view["dispatch_authorized"] is False


@pytest.mark.parametrize("change", ["missing_session", "missing_requirement", "wrong_revision", "wrong_root", "changed_script", "changed_source", "reopened", "tampered_ledger"])
def test_bad_acceptance_reference_stays_unknown(workspace, change, tmp_path):
    root, revision = workspace
    session, requirement = "case", "run"
    if change == "missing_session":
        session = "absent"
    elif change == "missing_requirement":
        requirement = "absent"
    elif change == "wrong_revision":
        revision = "f" * 40
    elif change == "wrong_root":
        other = tmp_path / "copied"
        shutil.copytree(root, other)
        root = other
    elif change == "changed_script":
        (root / "check.py").write_text("raise SystemExit(1)\n")
    elif change == "changed_source":
        (root / "artifact.txt").write_text("changed\n")
    elif change == "reopened":
        start_session(root, "case")
    else:
        path = root / ".showwork/claims/case.jsonl"
        path.write_bytes(path.read_bytes().replace(b"artifact exists", b"forged success"))
    view = example.read_evidence(root, session, requirement, revision)
    assert view["acceptance"]["state"] == ("incomplete" if change == "reopened" else "unknown")
    assert view["reference_status"] == "unknown"
    assert view["dispatch_authorized"] is False


def test_stopped_runtime_cannot_hide_failed_work(workspace):
    root, revision = workspace
    (root / "check.py").write_text("raise SystemExit(1)\n")
    git(root, "add", "check.py")
    git(root, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "failed attempt")
    revision = git(root, "rev-parse", "HEAD")
    start_session(root, "failed", ignore=["runtime.jsonl", "runtime-receipt.json"])
    record_requirement(root, "failed", "run", "check.py passes", "behavior",
        {"type": "command", "argv": ["python", "check.py"], "expect_exit": 0})
    record_claim(root, "failed", "check script exists", check={"type": "file_exists", "path": "check.py"})
    assert finish_session(root, "failed", "blocked")[0] == 0
    for stopped in (False, True):
        write_runtime(root, stopped=stopped)
        view = example.read_evidence(root, "failed", "run", revision)
        assert view["acceptance"]["state"] == "failed"
        assert view["runtime"]["state"] == ("stopped" if stopped else "no_recorded_stop")
        assert view["dispatch_authorized"] is False


def test_reader_never_executes_or_writes(workspace, monkeypatch):
    root, _ = workspace
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    def forbidden(*args, **kwargs):
        pytest.fail("read-only example attempted execution or write")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    assert read(workspace)["acceptance"]["state"] == "recorded_verified"
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_empty_workspace_and_prose_remain_unverified(tmp_path):
    empty = example.read_evidence(tmp_path, "case", "run", "f" * 40)
    assert empty["acceptance"]["state"] == "unknown"
    assert empty["runtime"]["state"] == "unknown"
    start_session(tmp_path, "case")
    record_claim(tmp_path, "case", "done")
    prose = example.read_evidence(tmp_path, "case", "run", "f" * 40)
    assert prose["acceptance"]["claim_state"] == "claimed"
    assert prose["reference_status"] == "unknown"
    assert prose["dispatch_authorized"] is False


def test_stopped_unfinished_requirements_remain_incomplete(workspace):
    root, revision = workspace
    start_session(root, "unfinished", ignore=["runtime.jsonl", "runtime-receipt.json"])
    record_requirement(root, "unfinished", "run", "must execute check", "behavior",
                       {"type": "command", "argv": ["python", "check.py"]})
    write_runtime(root, stopped=True)
    view = example.read_evidence(root, "unfinished", "run", revision)
    assert view["runtime"]["state"] == "stopped"
    assert view["acceptance"]["state"] == "incomplete"
    assert view["reference_status"] == "unknown"
    assert view["dispatch_authorized"] is False


def test_suite_documentation_links_and_retires_executable_bmd_recipe():
    repository = READER.parents[2]
    for relative in ("docs/suite-evidence.md", "examples/suite/README.md", "examples/bmd/README.md",
                     "docs/requests/bmd-overlay-receipts.md"):
        path = repository / relative
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://", "#")):
                continue
            assert (path.parent / target.split("#")[0]).resolve().exists(), (relative, target)
    bmd = (repository / "examples/bmd/README.md").read_text(encoding="utf-8")
    request = (repository / "docs/requests/bmd-overlay-receipts.md").read_text(encoding="utf-8")
    assert "from showwork.receipts import overlay_record" not in bmd
    assert "env.update(agent_environ" not in bmd
    assert "tracker: vault" in request
    assert "Do not copy this historical request" in request


def test_ambiguous_command_reference_is_unknown(workspace):
    """REGRESSION: a duplicate command reference returned loaded with unknown acceptance."""
    root, _ = workspace
    close = [row for row in load_all_events(root) if row.get("event") == "session.finish"][-1]
    payload = {key: value for key, value in close.items() if key not in {"event", "session", "ts", "prev"}}
    payload["command_evidence"] = payload["command_evidence"] * 2
    record_event(root, "session.finish", "case", **payload)
    view = read(workspace)
    assert view["acceptance"]["state"] == "unknown"
    assert view["acceptance"]["reference_bound"] is False
    assert view["reference_status"] == "unknown"
