"""Optional pytest plugin: record a receipt when --showwork-session is set.

Loaded only as a pytest plugin. showwork's runtime stays stdlib-only.
Without the flag the plugin does nothing, including in this repository's
own suite.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def pytest_addoption(parser):
    group = parser.getgroup("showwork")
    group.addoption(
        "--showwork-session",
        action="store",
        default="",
        help="If set, record an artifact file_contains claim for this pytest run.",
    )
    group.addoption(
        "--showwork-root",
        action="store",
        default="",
        help="Project root for the ledger (default: pytest rootdir).",
    )


def _now():
    return datetime.now(timezone.utc).isoformat()


def _revision(root):
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                                env=env, capture_output=True, text=True, timeout=5,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value) else None


def _write_latest(path, payload):
    """Readers see either the old or new complete JSON, never a partial write."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".pytest-latest-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(payload, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class _AttemptRecorder:
    def __init__(self, config, root, slug, artifacts):
        import pytest

        args = getattr(getattr(config, "invocation_params", None), "args", None)
        self.root, self.slug, self.artifacts = root, slug, artifacts
        self.counts = dict.fromkeys(("passed", "failed", "skipped", "errors", "xfailed", "xpassed"), 0)
        self.collected = None
        self.payload = {
            "session": slug, "exitstatus": None, "passed": None, "status": "running",
            "invocation_id": str(uuid.uuid4()), "started_at": _now(), "finished_at": None,
            "collected": None, "counts": None, "git_revision": None,
            "python_version": platform.python_version(), "python_executable": sys.executable,
            "pytest_version": pytest.__version__,
            "invocation_args_sha256": None if args is None else hashlib.sha256(
                json.dumps(list(args), ensure_ascii=False).encode("utf-8")).hexdigest(),
        }

    def pytest_collectreport(self, report):
        if report.failed:
            self.counts["errors"] += 1
        elif report.skipped:
            self.counts["skipped"] += 1

    def pytest_runtest_logreport(self, report):
        # pytest exposes strict XPASS as a string longrepr, without wasxfail.
        if (report.failed and report.when == "call" and isinstance(report.longrepr, str)
                and report.longrepr.startswith("[XPASS(strict)] ")):
            self.counts["xpassed"] += 1
        elif report.failed:
            self.counts["failed" if report.when == "call" else "errors"] += 1
        elif report.skipped:
            self.counts["xfailed" if hasattr(report, "wasxfail") else "skipped"] += 1
        elif report.passed and report.when == "call":
            self.counts["xpassed" if hasattr(report, "wasxfail") else "passed"] += 1


def pytest_sessionstart(session):
    slug = str(session.config.getoption("--showwork-session") or "").strip()
    if not slug:
        return
    root_opt = str(session.config.getoption("--showwork-root") or "").strip()
    root = Path(root_opt).resolve() if root_opt else Path(session.config.rootpath).resolve()
    from showwork.ledger import session_artifacts_dir, sessions_path, start_session

    artifacts = session_artifacts_dir(root, slug)
    artifacts.mkdir(parents=True, exist_ok=True)
    recorder = _AttemptRecorder(session.config, root, slug, artifacts)
    # Invalidate an old pass before the snapshot or optional Git probe can block.
    _write_latest(artifacts / "pytest-last.json", recorder.payload)
    if not sessions_path(root, slug).is_file():
        start_session(root, slug, agent="pytest")
    recorder.payload["git_revision"] = _revision(root)
    _write_latest(artifacts / "pytest-last.json", recorder.payload)
    started = artifacts / f"pytest-{recorder.payload['invocation_id']}-started.json"
    _retain_observation(recorder, started, recorder.payload,
                        f"pytest invocation {recorder.payload['invocation_id']} start observation retained")
    session.config._showwork_attempt = recorder
    session.config.pluginmanager.register(recorder, "showwork-attempt-recorder")


def pytest_collection_finish(session):
    recorder = getattr(session.config, "_showwork_attempt", None)
    if recorder is not None:
        # pytest assigns testscollected after this hook; items is already final.
        recorder.collected = len(session.items)


def _retain_observation(recorder, path, payload, claim):
    from showwork.ledger import record_claim
    content = json.dumps(payload)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content + "\n")
    record_claim(
        recorder.root, recorder.slug, claim,
        check={"type": "file_contains", "path": path.relative_to(recorder.root).as_posix(),
               "pattern": r"\A" + re.escape(content) + r"\n?\Z"},
    )


def pytest_sessionfinish(session, exitstatus):
    recorder = getattr(session.config, "_showwork_attempt", None)
    if recorder is None:
        return
    from showwork.ledger import record_claim

    payload = {**recorder.payload, "exitstatus": int(exitstatus), "passed": int(exitstatus) == 0,
               "status": "finished", "finished_at": _now(), "collected": recorder.collected,
               "counts": recorder.counts}
    invocation = payload["invocation_id"]
    attempt = recorder.artifacts / f"pytest-{invocation}.json"
    _retain_observation(recorder, attempt, payload,
                        f"pytest attempt {invocation} finish-hook observation retained")
    report = recorder.artifacts / "pytest-last.json"
    current = json.loads(report.read_text(encoding="utf-8"))
    if current.get("invocation_id") != invocation:
        return  # A later invocation owns latest; this attempt still has its immutable observation.
    _write_latest(report, payload)
    record_claim(
        recorder.root, recorder.slug, "Latest pytest report retains the session and finish-hook status",
        check={"type": "file_contains", "path": report.relative_to(recorder.root).as_posix(),
               "pattern": r'(?s)"session"\s*:\s*' + re.escape(json.dumps(recorder.slug))
                          + r'.{0,100}"status"\s*:\s*"finished"'},
    )
    if payload["passed"]:
        record_claim(recorder.root, recorder.slug, "pytest session passed",
                     check={"type": "file_contains", "path": report.relative_to(recorder.root).as_posix(),
                            "pattern": '"passed": true'})


def pytest_unconfigure(config):
    recorder = getattr(config, "_showwork_attempt", None)
    if recorder is not None:
        config.pluginmanager.unregister(recorder)
        del config._showwork_attempt
