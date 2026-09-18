"""Optional pytest plugin: record a receipt when --showwork-session is set.

Loaded only as a pytest plugin. showwork's runtime stays stdlib-only.
Without the flag the plugin does nothing, including in this repository's
own suite.
"""

from __future__ import annotations

import json
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


def pytest_sessionfinish(session, exitstatus):
    slug = str(session.config.getoption("--showwork-session") or "").strip()
    if not slug:
        return
    root_opt = str(session.config.getoption("--showwork-root") or "").strip()
    root = Path(root_opt).resolve() if root_opt else Path(session.config.rootpath).resolve()
    from showwork.ledger import session_artifacts_dir

    artifacts = session_artifacts_dir(root, slug)
    artifacts.mkdir(parents=True, exist_ok=True)
    report = artifacts / "pytest-last.json"
    passed = int(exitstatus) == 0
    payload = {
        "session": slug,
        "exitstatus": int(exitstatus),
        "passed": passed,
    }
    report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if not passed:
        return

    from showwork.ledger import record_claim, sessions_path, start_session

    try:
        events = sessions_path(root, slug)
    except ValueError:
        return
    if not events.is_file():
        start_session(root, slug, agent="pytest")
    record_claim(
        root,
        slug,
        "pytest session passed",
        check={
            "type": "file_contains",
            "path": report.relative_to(root).as_posix(),
            "pattern": '"passed": true',
        },
    )
