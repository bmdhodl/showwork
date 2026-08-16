"""Privacy boundary tests for the public replay sanitizer."""

from __future__ import annotations

import json

from scripts.build_public_dashboard import build
from scripts.sanitize_replay import sanitize


def test_sanitize_whitelists_untrusted_replay_fields():
    clean = sanitize(
        {
            "thresholds": {
                "repeat_threshold": 3,
                "window": 12,
                "secret": r"C:\Users\patri\private.json",
            },
            "scanned": r"C:\Users\patri\private.json",
            "with_calls": -1,
            "results": [
                {
                    "session": "session-id",
                    "project": r"C:\Users\patri\private-repo",
                    "total_calls": "many",
                    "stuck": "false",
                    "reason": "repeat",
                    "detail": r"Read called with identical input C:\Users\patri\secret",
                    "fired_at_call": -4,
                    "calls_after_trip": r"C:\Users\patri\secret",
                },
                {
                    "session": "another-session",
                    "project": "repo",
                    "reason": "untrusted-reason",
                    "detail": r"C:\Users\patri\raw detail",
                },
            ],
        }
    )

    assert clean["thresholds"] == {"repeat_threshold": 3, "window": 12}
    assert clean["scanned"] == 0
    assert clean["with_calls"] == 0
    first, second = clean["results"]
    assert first == {
        "session": first["session"],
        "project": "repo-1",
        "total_calls": 0,
        "stuck": False,
        "reason": "repeat",
        "detail": "Read called with identical input",
        "fired_at_call": None,
        "calls_after_trip": 0,
    }
    assert second["reason"] == "unknown"
    assert second["detail"] == "unclassified finding"
    assert "C:\\Users" not in json.dumps(clean)

    empty = sanitize({"results": [{"reason": "", "detail": ""}]})["results"][0]
    assert empty["reason"] == ""
    assert empty["detail"] == ""

    # The sanitized shape remains consumable by the public renderer.
    assert "private" not in build(clean)
