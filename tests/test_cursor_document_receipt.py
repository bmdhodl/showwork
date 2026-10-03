"""The retained Cursor correction receipt must reject removal of its facts."""

import json
from pathlib import Path

import pytest

from showwork.checks import evaluate_records


ROOT = Path(__file__).resolve().parents[1]
SESSION = "codex-cursor-availability-01a1000f"
REPORT = "docs/reports/cursor-availability-20261003"
PATHS = (
    "docs/host-recipes.md",
    "docs/reports/native-hosts-20261003.md",
    f"{REPORT}.md",
    f"{REPORT}/startup-observation.json",
    f"{REPORT}/first-observation.json",
)


@pytest.fixture
def receipt_workspace(tmp_path):
    for name in PATHS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    records = [json.loads(line) for line in
               (ROOT / f".showwork/claims/{SESSION}.jsonl").read_text(
                   encoding="utf-8").splitlines()]
    return tmp_path, records


def test_current_documents_satisfy_retained_receipt(receipt_workspace):
    root, records = receipt_workspace
    state = evaluate_records(records, root)
    assert state["verdict"] == "GREEN", state
    assert state["passed"] >= len(PATHS)


@pytest.mark.parametrize("path,original,replacement", [
    (PATHS[0], "`2026.09.15-d2fe57e`", "version unknown"),
    (PATHS[1], "Trust Required", "no trust refusal"),
    (PATHS[2], "field is therefore invalid", "field is valid"),
    (PATHS[3], '"persistent_terminal_session_marker_present": false',
     '"persistent_terminal_session_marker_present": true'),
    (PATHS[4], '"qualification":', '"unqualified_note":'),
])
def test_removed_correction_makes_retained_receipt_red(
        receipt_workspace, path, original, replacement):
    """REGRESSION: file-existence claims passed when the corrections disappeared."""
    root, records = receipt_workspace
    target = root / path
    text = target.read_text(encoding="utf-8")
    assert original in text, "The negative control must change an existing fact"
    target.write_text(text.replace(original, replacement), encoding="utf-8")
    state = evaluate_records(records, root)
    assert state["verdict"] == "RED", state
    assert any(row["status"] == "fail" for row in state["results"]), state
