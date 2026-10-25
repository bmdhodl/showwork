"""REGRESSION: status summaries must not replay historical commands (#193)."""

import json
import http.server
import subprocess
import threading

import pytest

from showwork.cli import main
from showwork.ledger import finish_session, record_claim, start_session
from showwork.outcomes import record_requirement
from showwork.report import session_status


@pytest.fixture
def http_sentinel(monkeypatch):
    monkeypatch.delenv("SHOWWORK_NO_NETWORK", raising=False)
    requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ready")

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/probe", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def http_session(root, sentinel, closed=True):
    url, requests = sentinel
    check = {"type": "http_probe", "url": url, "expect_status": 200,
             "body_contains": "ready"}
    start_session(root, "http-session")
    record_requirement(root, "http-session", "probe", "endpoint is ready", "artifact", check)
    record_claim(root, "http-session", "endpoint is ready", check=check)
    if closed:
        assert finish_session(root, "http-session")[0] == 0
        assert requests
        requests.clear()


@pytest.mark.parametrize("closed", [True, False])
@pytest.mark.parametrize("json_output", [True, False])
def test_REGRESSION_unscoped_status_does_not_probe_http(
        tmp_path, capsys, http_sentinel, closed, json_output):
    http_session(tmp_path, http_sentinel, closed=closed)
    args = ["--root", str(tmp_path), "status"]
    if json_output:
        args.append("--json")
    assert main(args) == 0
    output = capsys.readouterr().out
    assert http_sentinel[1] == []
    if json_output:
        row = json.loads(output)["sessions"][0]
        assert row["last_claims_verdict"] == ("GREEN" if closed else None)
        assert row["live_verdict"] == "YELLOW"
        assert row["live_passed"] == 0
        assert row["http_checks_not_run"] == 1
        assert row["command_checks_not_run"] == 0
        assert row["gaps"][0]["type"] == "http_probe"
    else:
        assert "http_checks=NOT_RUN (1)" in output
        assert "current_rerun=YELLOW" in output
        assert "--session" in output


def test_explicit_session_still_probes_http(tmp_path, capsys, http_sentinel):
    http_session(tmp_path, http_sentinel)
    assert main(["--root", str(tmp_path), "status", "--session", "http-session", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)["sessions"][0]
    assert http_sentinel[1] == ["/probe"]
    assert row["live_verdict"] == "GREEN"
    assert row["live_passed"] == 1
    assert row["http_checks_not_run"] == 0


def test_explicit_session_reports_failed_http_probe(tmp_path, capsys, http_sentinel):
    http_session(tmp_path, http_sentinel, closed=False)
    record_claim(tmp_path, "http-session", "endpoint is unavailable", check={
        "type": "http_probe", "url": http_sentinel[0], "expect_status": 503,
    })
    assert main(["--root", str(tmp_path), "status", "--session", "http-session", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)["sessions"][0]
    assert http_sentinel[1] == ["/probe", "/probe"]
    assert row["live_verdict"] == "RED"
    assert row["live_passed"] == 1
    assert row["http_checks_not_run"] == 0


def test_status_help_discloses_http_scope(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["status", "--help"])
    assert exc.value.code == 0
    assert "without commands or HTTP probes" in " ".join(capsys.readouterr().out.split())


def test_unscoped_status_counts_commands_and_http_separately(
        tmp_path, capsys, http_sentinel):
    command_session(tmp_path, closed=False)
    record_claim(tmp_path, "command-session", "endpoint is ready", check={
        "type": "http_probe", "url": http_sentinel[0], "expect_status": 200,
    })
    record_claim(tmp_path, "command-session", "missing local file exists", check={
        "type": "file_exists", "path": "missing.md",
    })
    assert main(["--root", str(tmp_path), "status", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)["sessions"][0]
    assert not (tmp_path / "sentinel").exists()
    assert http_sentinel[1] == []
    assert row["command_checks_not_run"] == 1
    assert row["http_checks_not_run"] == 1
    assert row["live_verdict"] == "RED"
    assert row["live_total"] == 3


def command_session(root, closed=True):
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "check.py").write_text(
        "from pathlib import Path\nPath('sentinel').write_text('ran')\nprint('passed')\n",
        encoding="utf-8",
    )
    start_session(root, "command-session")
    check = {"type": "command", "argv": ["python", "scripts/check.py"],
             "expect_exit": 0, "stdout_contains": "passed"}
    record_requirement(root, "command-session", "command", "script passes", "behavior", check)
    record_claim(root, "command-session", "script passes", check=check)
    if closed:
        assert finish_session(root, "command-session")[0] == 0
        (root / "sentinel").unlink()


@pytest.mark.parametrize("closed", [True, False])
def test_unscoped_status_does_not_run_command(tmp_path, capsys, closed):
    command_session(tmp_path, closed=closed)
    assert main(["--root", str(tmp_path), "status"]) == 0
    output = capsys.readouterr().out
    assert not (tmp_path / "sentinel").exists()
    assert "historical_finish=" + ("GREEN" if closed else "absent") in output
    assert "command_checks=NOT_RUN (1)" in output
    assert "current_rerun=YELLOW" in output
    assert "--session" in output


def test_unscoped_status_json_marks_command_unverified(tmp_path, capsys):
    command_session(tmp_path)
    assert main(["--root", str(tmp_path), "status", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)["sessions"][0]
    assert not (tmp_path / "sentinel").exists()
    assert row["last_claims_verdict"] == "GREEN"
    assert row["live_verdict"] == "YELLOW"
    assert row["live_passed"] == 0
    assert row["command_checks_not_run"] == 1
    assert row["gaps"][0]["type"] == "command"


def test_explicit_session_still_runs_command(tmp_path, capsys):
    command_session(tmp_path)
    assert main(["--root", str(tmp_path), "status", "--session", "command-session", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)["sessions"][0]
    assert (tmp_path / "sentinel").read_text() == "ran"
    assert row["live_verdict"] == "GREEN"
    assert row["live_passed"] == 1


@pytest.mark.parametrize("check", [
    {"type": "file_exists", "path": "data.md"},
    {"type": "file_contains", "path": "data.md", "pattern": "ready"},
    {"type": "glob_count", "pattern": "data.md", "op": "==", "n": 1},
    {"type": "frontmatter", "path": "data.md", "field": "status", "equals": "ready"},
    {"type": "git_state", "clean": True},
])
def test_unscoped_status_keeps_non_command_checks_live(tmp_path, check):
    data = tmp_path / "data.md"
    data.write_text("---\nstatus: ready\n---\nready\n", encoding="utf-8")
    if check["type"] == "git_state":
        (tmp_path / ".gitignore").write_text(".showwork/\n", encoding="utf-8")
        for args in (["init"], ["add", "data.md", ".gitignore"],
                     ["-c", "user.name=Test", "-c", "user.email=test@example.test",
                      "commit", "-m", "fixture"]):
            subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    start_session(tmp_path, "live")
    record_claim(tmp_path, "live", "current data", check=check)
    assert session_status(tmp_path)["sessions"][0]["live_verdict"] == "GREEN"
    data.unlink()
    assert session_status(tmp_path)["sessions"][0]["live_verdict"] == "RED"
