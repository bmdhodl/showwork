"""SW-04 publishes a zero pilot count until a real outside receipt exists."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = (ROOT / "docs" / "pilot.md").read_text(encoding="utf-8")
READOUT = (ROOT / "docs" / "reports" / "sw-04-pilot" / "README.md").read_text(encoding="utf-8")
TEMPLATE = (ROOT / ".github" / "ISSUE_TEMPLATE" / "pilot-report.yml").read_text(encoding="utf-8")


def test_readout_publishes_zero_numerator():
    """REGRESSION: a readout must not invent activations."""
    assert "Activations: 0/3." in READOUT
    assert "Repeat users: 0/2." in READOUT
    assert "No counted participant" in READOUT
    assert "first-value time" in READOUT
    assert "false refusals" in READOUT
    assert "setup abandonment" in READOUT
    assert "why plain CI was insufficient" in READOUT


def test_issue_64_is_not_an_activation():
    assert "issues/64" in READOUT
    assert "not an activation" in READOUT
    assert "0.3.0" in READOUT


def test_pilot_page_is_opt_in_and_points_at_the_behavior_walk():
    assert "quickstart-behavior.md" in PILOT
    assert "pilot-report.yml" in PILOT
    assert "No cold outreach" in PILOT or "no cold outreach" in PILOT
    assert "3 activations and 2 repeat users" in PILOT
    assert "intentional failure" in PILOT


def test_issue_template_requires_refusal_and_permission():
    assert "required: true" in TEMPLATE
    assert "REFUSED" in TEMPLATE
    assert "redacted proof" in TEMPLATE
    assert "at least 7 days later" in TEMPLATE
    assert "showwork owner" in TEMPLATE
