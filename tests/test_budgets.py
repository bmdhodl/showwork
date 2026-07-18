"""Tests for run budgets."""

from __future__ import annotations

import pytest

from showwork.budgets import BudgetVerdict, RunBudget


class FakeClock:
    """Injectable monotonic clock, so budgets are testable without sleeping."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# -- tool-call ceilings -----------------------------------------------------


def test_budget_permits_exactly_n_calls():
    budget = RunBudget(max_tool_calls=3, clock=FakeClock())
    for _ in range(3):
        assert not budget.record("Read").exceeded
    assert budget.record("Read").exceeded


def test_tool_call_verdict_explains_itself():
    budget = RunBudget(max_tool_calls=1, clock=FakeClock())
    budget.record("Read")
    verdict = budget.record("Read")
    assert verdict.reason == "tool_calls"
    assert "exceeded 1 tool calls" in verdict.detail


def test_unlimited_by_default():
    budget = RunBudget(clock=FakeClock())
    for _ in range(500):
        assert not budget.record("Read").exceeded


# -- wall clock -------------------------------------------------------------


def test_time_budget_trips_when_exceeded():
    clock = FakeClock()
    budget = RunBudget(max_seconds=60, clock=clock)
    budget.record("Read")
    clock.advance(61)
    verdict = budget.record("Read")
    assert verdict.exceeded
    assert verdict.reason == "time"


def test_time_budget_boundary_is_inclusive():
    clock = FakeClock()
    budget = RunBudget(max_seconds=60, clock=clock)
    budget.record("Read")
    clock.advance(60)
    assert not budget.record("Read").exceeded


def test_check_catches_time_without_a_tool_call():
    """A run can blow its clock while blocked on one slow call."""
    clock = FakeClock()
    budget = RunBudget(max_seconds=10, clock=clock)
    budget.record("Bash")
    clock.advance(30)
    assert budget.check().exceeded


def test_check_before_start_is_within_budget():
    assert not RunBudget(max_seconds=1, clock=FakeClock()).check().exceeded


# -- per-tool rate ----------------------------------------------------------


def test_per_tool_cap_is_independent_of_total():
    budget = RunBudget(max_calls_per_tool={"Bash": 2}, clock=FakeClock())
    for _ in range(20):
        assert not budget.record("Read").exceeded
    assert not budget.record("Bash").exceeded
    assert not budget.record("Bash").exceeded
    verdict = budget.record("Bash")
    assert verdict.exceeded
    assert verdict.reason == "tool_rate"
    assert "Bash exceeded 2 calls" in verdict.detail


def test_untracked_tools_are_unlimited():
    budget = RunBudget(max_calls_per_tool={"Bash": 1}, clock=FakeClock())
    for _ in range(50):
        assert not budget.record("Read").exceeded


# -- latching + lifecycle ---------------------------------------------------


def test_verdict_latches_until_reset():
    budget = RunBudget(max_tool_calls=1, clock=FakeClock())
    budget.record("Read")
    first = budget.record("Read")
    assert first.exceeded
    assert budget.record("Read").reason == first.reason

    budget.reset()
    assert not budget.record("Read").exceeded


def test_start_is_idempotent():
    clock = FakeClock()
    budget = RunBudget(max_seconds=10, clock=clock)
    budget.start()
    clock.advance(5)
    budget.start()  # must not restart the clock
    clock.advance(6)
    assert budget.check().exceeded


def test_counters_are_observable():
    budget = RunBudget(clock=FakeClock())
    for _ in range(4):
        budget.record("Read")
    assert budget.calls == 4


# -- construction -----------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_seconds": 0},
        {"max_seconds": -1},
        {"max_tool_calls": 0},
        {"max_calls_per_tool": {"Bash": 0}},
    ],
)
def test_unusable_limits_are_rejected_loudly(kwargs):
    with pytest.raises(ValueError):
        RunBudget(clock=FakeClock(), **kwargs)


def test_verdict_serialises_for_the_ledger():
    payload = BudgetVerdict(exceeded=True, reason="time", detail="x").as_dict()
    assert payload == {"exceeded": True, "reason": "time", "detail": "x"}
