"""Cross-implementation conformance: the Python reference auditor must match
the frozen chain fixtures that js/showwork-audit is also held to."""

import json
from pathlib import Path

import pytest

from showwork.audit import audit_file

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "chain"
EXPECTED = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_fixture_verdicts_match_contract(name):
    want = EXPECTED[name]
    got = audit_file(FIXTURES / name)
    assert got["verdict"] == want["verdict"], name
    assert got["break_at"] == want["break_at"], name
    for key in ("chained", "pre_chain", "forks"):
        if key in want:
            assert got[key] == want[key], f"{name}: {key}"
