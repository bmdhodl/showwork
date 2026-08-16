"""Privacy boundary tests for the public replay sanitizer."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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
                {
                    "session": "private-tool",
                    "project": "repo",
                    "reason": "repeat",
                    "detail": "alice_private_repo called with identical input",
                },
                {
                    "session": "customer-mcp",
                    "project": "repo",
                    "reason": "repeat",
                    "detail": "mcp__customer_acme__lookup called with identical input",
                },
                {
                    "session": "known-tool",
                    "project": "repo",
                    "reason": "repeat",
                    "detail": "Bash called with identical input",
                },
            ],
        }
    )

    assert clean["thresholds"] == {"repeat_threshold": 3, "window": 12}
    assert clean["scanned"] == 5
    assert clean["with_calls"] == 5
    first, second, private, customer_mcp, known = clean["results"]
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
    assert private["detail"] == "unknown tool called with identical input"
    assert customer_mcp["detail"] == "unknown tool called with identical input"
    assert known["detail"] == "Bash called with identical input"
    assert "C:\\Users" not in json.dumps(clean)

    empty = sanitize({"results": [{"reason": "", "detail": ""}]})["results"][0]
    assert empty["reason"] == ""
    assert empty["detail"] == ""

    # The sanitized shape remains consumable by the public renderer.
    assert "private" not in build(clean)


def test_sanitize_is_idempotent_for_approved_public_shape():
    raw = {
        "thresholds": {"repeat_threshold": 3},
        "scanned": 1,
        "with_calls": 1,
        "results": [
            {
                "session": "deadbee",
                "project": r"C:\Users\patri\private-repo",
                "total_calls": 4,
                "stuck": True,
                "reason": "repeat",
                "detail": "Read called with identical input C:\\secret",
                "fired_at_call": 3,
                "calls_after_trip": 1,
            }
        ],
    }

    clean = sanitize(raw)
    assert clean["results"][0]["session"].startswith("run-")
    assert clean["results"][0]["session"] != "deadbee"
    assert sanitize(clean) is clean
    assert sanitize(clean) == clean


def test_sanitize_rehashes_transcript_supplied_public_looking_session_id():
    clean = sanitize(
        {"results": [{"session": "run-deadbee", "reason": ""}]}
    )

    assert clean["results"][0]["session"] != "run-deadbee"
    assert clean["results"][0]["session"].startswith("run-")


def test_public_renderer_falls_back_for_invalid_explicit_with_calls():
    rendered = build(
        {
            "with_calls": "not-a-count",
            "results": [{"session": "raw", "stuck": True}],
        }
    )

    assert "100.0%" in rendered


def test_public_renderer_falls_back_for_inconsistent_explicit_with_calls():
    rendered = build(
        {
            "with_calls": 100,
            "results": [{"session": "raw", "stuck": True}],
        }
    )

    assert "100.0%" in rendered


def test_public_renderer_clamps_scanned_to_emitted_rows():
    rendered = build(
        {
            "scanned": 0,
            "with_calls": 1,
            "results": [{"session": "raw", "stuck": True}],
        }
    )

    assert '1</span><span class="l">sessions replayed' in rendered


def test_public_renderer_sanitizes_raw_input_even_when_attested_by_caller():
    rendered = build(
        {
            "sanitized": True,
            "scanned": r"C:\Users\patri\private.json",
            "results": [
                {
                    "session": "raw-session",
                    "project": r"C:\Users\patri\private-repo",
                    "total_calls": 4,
                    "stuck": True,
                    "reason": "repeat",
                    "detail": (
                        "mcp__customer_acme__lookup called with identical input "
                        r"C:\Users\patri\secret"
                    ),
                    "fired_at_call": 3,
                    "calls_after_trip": 1,
                }
            ],
        }
    )

    assert "mcp__customer_acme__lookup" not in rendered
    assert "C:\\Users" not in rendered
    assert "unknown tool" in rendered


def test_public_renderer_cli_sanitizes_forged_marker_input(tmp_path):
    source = tmp_path / "forged.json"
    output = tmp_path / "dashboard.html"
    source.write_text(
        json.dumps(
            {
                "sanitized": True,
                "scanned": r"C:\Users\patri\private.json",
                "results": [
                    {
                        "session": "raw-session",
                        "project": r"C:\Users\patri\private-repo",
                        "total_calls": 4,
                        "stuck": True,
                        "reason": "repeat",
                        "detail": (
                            "alice_private_repo called with identical input "
                            r"C:\Users\patri\secret"
                        ),
                        "fired_at_call": 3,
                        "calls_after_trip": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_public_dashboard.py",
            "--replay",
            str(source),
            "--out",
            str(output),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    rendered = output.read_text(encoding="utf-8")
    assert "alice_private_repo" not in rendered
    assert "C:\\Users" not in rendered
    assert "unknown tool" in rendered
    assert "100.0%" in rendered
