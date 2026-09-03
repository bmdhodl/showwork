"""Read-only BMD receipt overlay: four states, no writes, empty is unknown."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from showwork.cli import main
from showwork.ledger import sessions_path
from showwork.receipts import (
    agent_environ,
    agent_prompt_block,
    decorate_records,
    evidence_for_session,
    overlay_record,
    receipts_payload,
    render_badges_html,
    session_for_task,
    sidecar_interpreter,
)


def _tree_fingerprint(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        mtime = str(path.stat().st_mtime_ns)
        out[rel] = f"{digest}:{mtime}"
    return out


def _run(root: Path, *argv: str) -> int:
    return main(["--root", str(root), *argv])


def test_session_for_task_is_stable():
    assert session_for_task("abc") == "bmd-abc"
    assert session_for_task("bmd-abc") == "bmd-abc"


def test_empty_workspace_is_unknown(tmp_path):
    payload = receipts_payload(tmp_path, task_id="first")
    assert payload["empty"] is True
    row = payload["records"][0]["verification"]
    assert row["state"] == "unknown"
    assert "No receipts yet" in row["reason"]


def test_green_session_is_verified(tmp_path):
    (tmp_path / "out.md").write_text("shipped: yes", encoding="utf-8")
    assert _run(tmp_path, "start", "--session", "bmd-green", "--agent", "test") == 0
    assert _run(
        tmp_path, "claim", "--session", "bmd-green",
        "--claim", "wrote out.md", "--type", "file_contains",
        "--path", "out.md", "--pattern", "shipped",
    ) == 0
    assert _run(tmp_path, "finish", "--session", "bmd-green") == 0
    evidence = evidence_for_session(tmp_path, "bmd-green")
    assert evidence["state"] == "verified"
    assert evidence["claim"] == "wrote out.md"


def test_red_session_is_failed(tmp_path):
    assert _run(tmp_path, "start", "--session", "bmd-red") == 0
    assert _run(
        tmp_path, "claim", "--session", "bmd-red",
        "--claim", "made a file", "--type", "file_exists",
        "--path", "never-created.txt",
    ) == 0
    assert _run(tmp_path, "finish", "--session", "bmd-red") == 2
    evidence = evidence_for_session(tmp_path, "bmd-red")
    assert evidence["state"] == "failed"
    assert evidence["claim"] == "made a file"


def test_prose_only_session_is_claimed(tmp_path):
    assert _run(tmp_path, "start", "--session", "bmd-prose") == 0
    assert _run(tmp_path, "claim", "--session", "bmd-prose", "--claim", "vibes only") == 0
    assert _run(tmp_path, "finish", "--session", "bmd-prose") == 2
    evidence = evidence_for_session(tmp_path, "bmd-prose")
    assert evidence["state"] == "claimed"


def test_broken_jsonl_is_unknown(tmp_path):
    session = "bmd-broke"
    assert _run(tmp_path, "start", "--session", session) == 0
    path = sessions_path(tmp_path, session)
    path.write_bytes(b"\xff\xfe not json\n")
    evidence = evidence_for_session(tmp_path, session)
    assert evidence["state"] == "unknown"
    assert "unreadable" in evidence["reason"]


def test_overlay_joins_task_id(tmp_path):
    (tmp_path / "ok.txt").write_text("ok", encoding="utf-8")
    assert _run(tmp_path, "start", "--session", "bmd-task-9") == 0
    assert _run(
        tmp_path, "claim", "--session", "bmd-task-9",
        "--claim", "ok.txt exists", "--type", "file_exists", "--path", "ok.txt",
    ) == 0
    overlay = overlay_record({"task_id": "task-9"}, tmp_path)
    assert overlay is not None
    assert overlay["state"] == "verified"


def test_overlay_without_session_is_none(tmp_path):
    assert overlay_record({"status": "done"}, tmp_path) is None


def test_overlay_does_not_write(tmp_path):
    (tmp_path / "ok.txt").write_text("ok", encoding="utf-8")
    assert _run(tmp_path, "start", "--session", "bmd-ro") == 0
    assert _run(
        tmp_path, "claim", "--session", "bmd-ro",
        "--claim", "ok.txt exists", "--type", "file_exists", "--path", "ok.txt",
    ) == 0
    before = _tree_fingerprint(tmp_path)
    decorate_records(
        [{"task_id": "ro", "title": "run", "surface": "activity"}],
        tmp_path,
    )
    evidence_for_session(tmp_path, "bmd-ro")
    receipts_payload(tmp_path, task_id="ro")
    after = _tree_fingerprint(tmp_path)
    assert after == before


def test_receipts_module_source_has_no_write_calls():
    src = Path(__file__).resolve().parents[1] / "src" / "showwork" / "receipts.py"
    text = src.read_text(encoding="utf-8")
    for name in ("record_claim(", "record_event(", "record_retraction(",
                 "start_session(", "finish_session("):
        assert name not in text, name


def test_dispatch_prompt_names_session_not_vault_paths():
    block = agent_prompt_block("fix-nav", interpreter="/opt/BMD/bmd-server", agent="codex")
    env = agent_environ("/tmp/workspace", "fix-nav", interpreter="/opt/BMD/bmd-server")
    assert "bmd-fix-nav" in block
    assert "SHOWWORK_ROOT" in block
    assert env["SHOWWORK_SESSION"] == "bmd-fix-nav"
    assert env["SHOWWORK_PYTHON"] == "/opt/BMD/bmd-server"
    lowered = block.lower()
    assert "obsidian" not in lowered
    assert "vault" not in lowered
    assert "users/patri" not in lowered
    assert "fluarmn" not in lowered


def test_sidecar_interpreter_help():
    exe = sidecar_interpreter()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    proc = subprocess.run(
        [exe, "-m", "showwork", "--help"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0
    assert "receipts" in proc.stdout


def test_cli_receipts_json_empty(tmp_path, capsys):
    assert _run(tmp_path, "receipts", "--task-id", "none", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["records"][0]["verification"]["state"] == "unknown"


def test_cli_receipts_html(tmp_path, capsys):
    html_path = tmp_path / "badges.html"
    assert _run(tmp_path, "receipts", "--task-id", "none", "--html", str(html_path)) == 0
    text = html_path.read_text(encoding="utf-8")
    assert 'data-state="unknown"' in text
    assert ">VERIFIED</summary>" not in text
    capsys.readouterr()
