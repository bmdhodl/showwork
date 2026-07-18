"""Behavioural tests for stuck detection.

The most important tests here are the negative ones. A guard that kills real
work gets disabled by its operator, and a disabled guard catches nothing. Every
"must NOT trip" case below is protecting that.
"""

from __future__ import annotations

import pytest

from showwork.guards import StuckDetector, StuckVerdict, ToolCall, fingerprint, scan


def read(name: str = "Read", **kwargs) -> ToolCall:
    """A non-mutating call."""
    return ToolCall(tool_name=name, tool_input=kwargs, mutated=False)


def write(name: str = "Write", **kwargs) -> ToolCall:
    """A mutating call."""
    return ToolCall(tool_name=name, tool_input=kwargs, mutated=True)


# -- repeat -----------------------------------------------------------------


def test_identical_call_trips_at_threshold():
    calls = [read("Bash", cmd="pytest") for _ in range(3)]
    verdict = scan(calls, repeat_threshold=3)
    assert verdict.stuck
    assert verdict.reason == "repeat"
    assert "3 times" in verdict.detail


def test_identical_call_below_threshold_does_not_trip():
    calls = [read("Bash", cmd="pytest") for _ in range(2)]
    assert not scan(calls, repeat_threshold=3).stuck


def test_repeat_needs_identical_input_not_just_identical_tool():
    # Same tool, different arguments each time. That is normal work.
    calls = [read("Read", path=f"file{i}.py") for i in range(10)]
    assert not scan(calls, repeat_threshold=3, no_progress_threshold=None).stuck


def test_repeats_outside_the_window_do_not_accumulate():
    detector = StuckDetector(repeat_threshold=3, window=4, no_progress_threshold=None)
    target = read("Bash", cmd="pytest")
    # Two hits, then enough distinct calls to push them out of the window.
    detector.observe(target)
    detector.observe(target)
    for i in range(4):
        detector.observe(read("Read", path=f"f{i}.py"))
    assert not detector.observe(target).stuck


# -- alternation ------------------------------------------------------------


def test_abab_ping_pong_trips():
    a = read("Edit", path="a.py")
    b = read("Edit", path="b.py")
    verdict = scan([a, b, a, b, a, b], alternation_threshold=3, repeat_threshold=None, no_progress_threshold=None)
    assert verdict.stuck
    assert verdict.reason == "alternation"


def test_short_alternation_does_not_trip():
    a = read("Edit", path="a.py")
    b = read("Edit", path="b.py")
    verdict = scan([a, b, a, b], alternation_threshold=3, repeat_threshold=None, no_progress_threshold=None)
    assert not verdict.stuck


def test_broken_alternation_does_not_trip():
    a = read("Edit", path="a.py")
    b = read("Edit", path="b.py")
    c = read("Edit", path="c.py")
    verdict = scan([a, b, a, c, a, b], alternation_threshold=3, repeat_threshold=None, no_progress_threshold=None)
    assert not verdict.stuck


# -- no progress ------------------------------------------------------------


def test_consecutive_non_mutating_calls_trip():
    calls = [read("Read", path=f"f{i}.py") for i in range(6)]
    verdict = scan(calls, no_progress_threshold=6, repeat_threshold=None)
    assert verdict.stuck
    assert verdict.reason == "no_progress"
    assert "6 consecutive" in verdict.detail


def test_mutation_resets_the_no_progress_counter():
    detector = StuckDetector(no_progress_threshold=4, repeat_threshold=None)
    for i in range(3):
        assert not detector.observe(read("Read", path=f"f{i}.py")).stuck
    # Real progress.
    assert not detector.observe(write("Write", path="out.py")).stuck
    # Counter restarts, so three more reads are still fine.
    for i in range(3):
        assert not detector.observe(read("Read", path=f"g{i}.py")).stuck


# -- false positives: the ones that matter ----------------------------------


def test_slow_but_progressing_agent_never_trips():
    """Twelve reads per edit, sustained. Slow, thorough, and NOT stuck."""
    detector = StuckDetector(repeat_threshold=3, window=12, no_progress_threshold=6)
    for cycle in range(20):
        for i in range(4):
            assert not detector.observe(read("Read", path=f"c{cycle}-{i}.py")).stuck
        assert not detector.observe(write("Edit", path=f"c{cycle}.py")).stuck
    assert not detector.tripped


def test_varied_productive_work_never_trips():
    detector = StuckDetector()
    tools = ["Read", "Edit", "Bash", "Grep", "Write"]
    for i in range(100):
        call = ToolCall(
            tool_name=tools[i % len(tools)],
            tool_input={"path": f"file{i}.py"},
            mutated=(i % 3 == 0),
        )
        assert not detector.observe(call).stuck
    assert not detector.tripped


def test_retrying_with_different_fixes_is_not_stuck():
    """Re-running the same test after each edit is convergent work."""
    detector = StuckDetector(repeat_threshold=3, no_progress_threshold=6)
    for i in range(10):
        assert not detector.observe(write("Edit", path=f"fix{i}.py")).stuck
        assert not detector.observe(read("Bash", cmd="pytest")).stuck
    assert not detector.tripped


# -- latching ---------------------------------------------------------------


def test_verdict_latches_until_reset():
    detector = StuckDetector(repeat_threshold=2, no_progress_threshold=None)
    target = read("Bash", cmd="pytest")
    detector.observe(target)
    first = detector.observe(target)
    assert first.stuck

    # Even obviously-productive work does not un-stick a killed run.
    again = detector.observe(write("Write", path="new.py"))
    assert again.stuck
    assert again.reason == first.reason

    detector.reset()
    assert not detector.tripped
    assert not detector.observe(write("Write", path="new.py")).stuck


# -- fingerprinting ---------------------------------------------------------


def test_dict_key_order_does_not_change_identity():
    assert fingerprint("Edit", {"a": 1, "b": 2}) == fingerprint("Edit", {"b": 2, "a": 1})


def test_different_tools_with_same_input_differ():
    assert fingerprint("Read", {"p": 1}) != fingerprint("Write", {"p": 1})


def test_unserialisable_input_does_not_raise():
    class Opaque:
        pass

    # Must not explode; identity just falls back to repr.
    assert fingerprint("Tool", Opaque())


# -- verdict + construction -------------------------------------------------


def test_verdict_serialises_for_the_ledger():
    verdict = scan([read("Bash", cmd="x") for _ in range(3)], repeat_threshold=3)
    payload = verdict.as_dict()
    assert payload["stuck"] is True
    assert payload["reason"] == "repeat"
    assert isinstance(payload["evidence"], list)


def test_clean_run_reports_not_stuck():
    assert StuckVerdict(stuck=False).as_dict()["stuck"] is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"repeat_threshold": 1},
        {"alternation_threshold": 1},
        {"no_progress_threshold": 1},
        {"window": 1},
        {"window": 3, "repeat_threshold": 5},  # can never trip
    ],
)
def test_unusable_thresholds_are_rejected_loudly(kwargs):
    with pytest.raises(ValueError):
        StuckDetector(**kwargs)


def test_empty_stream_is_not_stuck():
    assert not scan([]).stuck


# -- calibration regression -------------------------------------------------


def test_no_progress_is_off_by_default():
    """Replaying 2,757 real sessions showed no_progress=6 flagged 82.7% of them.

    Reading a dozen files before an edit is ordinary work. This default shipped
    wrong while every synthetic test above passed, so it is pinned here: if
    someone re-enables it by default, that decision must be deliberate and must
    be re-validated against real transcripts.
    """
    detector = StuckDetector()
    assert detector.no_progress_threshold is None
    # 30 consecutive reads, all distinct: normal exploration, must not trip.
    for i in range(30):
        assert not detector.observe(read("Read", path=f"f{i}.py")).stuck


def test_no_progress_still_available_when_asked_for():
    detector = StuckDetector(no_progress_threshold=6, repeat_threshold=None)
    verdict = detector.observe_all([read("Read", path=f"f{i}.py") for i in range(6)])
    assert verdict.stuck and verdict.reason == "no_progress"


def test_repeat_catches_the_real_world_polling_loop():
    """The shape actually found in production: identical API call, unchanged args."""
    detector = StuckDetector()
    call = read("mcp__kraken__fetchBalance", account="main")
    assert not detector.observe(call).stuck
    assert not detector.observe(call).stuck
    assert detector.observe(call).stuck
