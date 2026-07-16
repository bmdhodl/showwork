"""FDR analyzer: eligibility, false-done evidence classes, rates."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from false_done_rate import analyze_root  # noqa: E402

from showwork.ledger import (  # noqa: E402
    finish_session,
    record_claim,
    record_event,
    record_retraction,
    start_session,
)


def _touch(root: Path, name: str) -> str:
    (root / name).write_text("x", encoding="utf-8")
    return name


def test_clean_session_is_eligible_not_false(tmp_path):
    start_session(tmp_path, "clean", agent="a1")
    record_claim(tmp_path, "clean", "made f",
                 check={"type": "file_exists", "path": _touch(tmp_path, "f")})
    assert finish_session(tmp_path, "clean")[0] == 0
    r = analyze_root(tmp_path)
    assert r["eligible_sessions"] == 1
    assert r["false_done_sessions"] == 0
    assert r["fdr_session"] == 0.0


def test_refused_close_is_false_done(tmp_path):
    start_session(tmp_path, "liar")
    record_claim(tmp_path, "liar", "made g",
                 check={"type": "file_exists", "path": "missing.txt"})
    assert finish_session(tmp_path, "liar")[0] == 2  # REFUSED
    _touch(tmp_path, "missing.txt")
    assert finish_session(tmp_path, "liar")[0] == 0
    r = analyze_root(tmp_path)
    assert r["false_done_sessions"] == 1
    assert r["sessions"]["liar"]["refused"] == 1
    assert r["fdr_session"] == 1.0


def test_retraction_counts_as_false_done(tmp_path):
    start_session(tmp_path, "s")
    record_claim(tmp_path, "s", "bad claim",
                 check={"type": "file_exists", "path": "nope"})
    record_retraction(tmp_path, "s", "bad claim", "was wrong")
    record_claim(tmp_path, "s", "good claim",
                 check={"type": "file_exists", "path": _touch(tmp_path, "ok")})
    assert finish_session(tmp_path, "s")[0] == 0
    r = analyze_root(tmp_path)
    assert r["false_done_sessions"] == 1
    assert r["sessions"]["s"]["retractions"] == 1


def test_bypass_counts_as_false_done(tmp_path):
    start_session(tmp_path, "b")
    record_claim(tmp_path, "b", "unverified",
                 check={"type": "file_exists", "path": "ghost"})
    assert finish_session(tmp_path, "b", no_verify=True)[0] == 0
    r = analyze_root(tmp_path)
    assert r["sessions"]["b"]["bypassed"] == 1
    assert r["false_done_sessions"] == 1


def test_uncheckable_session_not_eligible(tmp_path):
    start_session(tmp_path, "prose")
    record_claim(tmp_path, "prose", "vibes only")  # no check
    finish_session(tmp_path, "prose")
    r = analyze_root(tmp_path)
    assert r["eligible_sessions"] == 0
    assert r["fdr_session"] is None
