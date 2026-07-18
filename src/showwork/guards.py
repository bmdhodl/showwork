"""Stuck detection for long-running agents.

Gateways enforce on dollars. They see requests, not agent semantics, so they
cannot tell a productive agent from one that has been retrying the same failing
command for twenty minutes. Both look like spend.

This module reads the tool-call stream instead. It answers one question: is this
agent still making progress, or is it stuck? Three signatures count as stuck:

``repeat``
    The same tool called with the same input N times inside a window. The
    classic "re-run the failing test and hope" loop.

``alternation``
    A-B-A-B ping-pong. Two tools undoing each other, which never converges and
    never trips a naive same-call-twice check.

``no_progress``
    N consecutive calls that mutated nothing. **Off by default** — see below.

Calibration (2026-07-18, 2,757 real Claude Code sessions, 4,674 transcripts
replayed via ``scripts/replay_transcripts.py``):

===================  ==================  ============================
signature            sessions flagged    read
===================  ==================  ============================
repeat (3, win 12)   14  (0.5%)          plausible true positives
no_progress (6)      2281 (82.7%)        noise
no_progress (20)     248  (9.0%)         still mostly noise
no_progress (80+)    0 beyond repeat     adds nothing
alternation (3)      0                   never fired on real data
===================  ==================  ============================

``no_progress`` shipped at 6 and would have killed **four out of five real
sessions**. Reading a dozen files before making an edit is ordinary work, not a
stall, and "did not mutate" turns out to be a terrible proxy for "is not
progressing". Raising the threshold did not rescue it: by the point it stopped
firing on healthy sessions it had stopped firing on anything ``repeat`` had not
already caught. It is off by default and kept only for callers who know their
workload.

Every synthetic test in ``tests/test_guards.py`` passed while that default was
wrong. Fixtures prove the code does what it was written to do; only real
transcripts tell you whether it was written to do the right thing.

What ``repeat`` actually catches on real data: browser automation re-clicking
identical coordinates, API polling loops (``fetchBalance``, ``get_account_info``
with unchanged arguments), and the same file read three times inside five calls.
One flagged session ran **813 further tool calls** after the point of detection.

Deliberately NOT here: token, cost, or dollar budgets. Anthropic's gateway and
Cloudflare AI Gateway both enforce spend natively, and Claude Code hooks receive
no cost data at all (claude-code#11008, open since 2025-11-04). Detecting a
stuck agent needs none of it — the tool stream is enough, and it fires *before*
the dollars are spent rather than after.

A kill without a receipt is worth nothing, so every trip returns a
:class:`StuckVerdict` carrying the evidence that justified it.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

__all__ = [
    "StuckDetector",
    "StuckVerdict",
    "ToolCall",
    "fingerprint",
]

# A window smaller than the threshold can never trip; reject it loudly rather
# than silently never firing.
_MIN_WINDOW = 2


def fingerprint(tool_name: str, tool_input: Any) -> str:
    """Stable identity for a tool call.

    Two calls are "the same" when the tool and its arguments match. Input is
    serialised with sorted keys so that dict ordering never changes identity.
    Unserialisable input falls back to ``repr``, which is stable enough for
    equality within a single run.
    """
    try:
        rendered = json.dumps(tool_input, sort_keys=True, default=repr)
    except (TypeError, ValueError):
        rendered = repr(tool_input)
    return f"{tool_name}\x00{rendered}"


@dataclass(frozen=True)
class ToolCall:
    """One observed tool call.

    ``mutated`` is the caller's answer to "did this change the world?" — files
    written, commands with side effects, records created. Read-only calls pass
    ``False``. Callers that cannot tell should pass ``True``; over-reporting
    mutation makes the detector more conservative, never more aggressive.
    """

    tool_name: str
    tool_input: Any = None
    mutated: bool = False

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.tool_name, self.tool_input)


@dataclass(frozen=True)
class StuckVerdict:
    """The result of observing one call.

    ``stuck`` is the only field callers must branch on. The rest exists so the
    evidence pack can say precisely what happened and why it was defensible.
    """

    stuck: bool
    reason: str = ""
    detail: str = ""
    evidence: tuple[str, ...] = field(default=())

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return self.stuck

    def as_dict(self) -> dict:
        """Serialisable form, for the ledger and evidence packs."""
        return {
            "stuck": self.stuck,
            "reason": self.reason,
            "detail": self.detail,
            "evidence": list(self.evidence),
        }


_NOT_STUCK = StuckVerdict(stuck=False)


class StuckDetector:
    """Observe a tool-call stream and report when the agent stops progressing.

    The detector is deliberately conservative. A false positive kills real work
    and teaches the operator to disable the guard, which is worse than missing a
    loop. Every threshold therefore requires *consecutive* or *windowed*
    evidence, and any mutation resets the no-progress counter.

    Thresholds are counts of occurrences, not "extras": ``repeat_threshold=3``
    fires on the third identical call, not the fourth.
    """

    def __init__(
        self,
        *,
        repeat_threshold: int | None = 3,
        window: int = 12,
        no_progress_threshold: int | None = None,
        alternation_threshold: int | None = 3,
    ) -> None:
        if repeat_threshold is not None and repeat_threshold < 2:
            raise ValueError("repeat_threshold must be >= 2, or None to disable")
        if alternation_threshold is not None and alternation_threshold < 2:
            raise ValueError("alternation_threshold must be >= 2, or None to disable")
        if no_progress_threshold is not None and no_progress_threshold < 2:
            raise ValueError("no_progress_threshold must be >= 2, or None to disable")
        if window < _MIN_WINDOW:
            raise ValueError(f"window must be >= {_MIN_WINDOW}")
        if repeat_threshold is not None and window < repeat_threshold:
            raise ValueError("window must be >= repeat_threshold, or it can never trip")

        self.repeat_threshold = repeat_threshold
        self.window = window
        self.no_progress_threshold = no_progress_threshold
        # An A-B-A-B run of length 2N contains N repeats of each side.
        self.alternation_threshold = alternation_threshold

        self._recent: deque[str] = deque(maxlen=window)
        self._since_progress = 0
        self._tripped = False

    @property
    def tripped(self) -> bool:
        """True once a verdict has fired. The detector latches."""
        return self._tripped

    def reset(self) -> None:
        """Clear all state, including the latch."""
        self._recent.clear()
        self._since_progress = 0
        self._tripped = False

    def observe(self, call: ToolCall) -> StuckVerdict:
        """Record one call and return the current verdict.

        Latches: once stuck, every subsequent observation returns the same
        verdict until :meth:`reset`. A run that has been declared stuck should
        be killed, not re-evaluated.
        """
        if self._tripped:
            return self._last

        if call.mutated:
            # Real progress clears the slate. Every signature below measures
            # "stuck SINCE the last real change", not "repetitive ever".
            #
            # This is the difference between a loop and a retry. edit -> test ->
            # edit -> test runs the same test command every cycle, but each
            # cycle changed the world, so it is convergent work and must never
            # be killed. Without this reset the most common productive agent
            # pattern in existence trips the repeat guard on its third cycle.
            self._recent.clear()
            self._since_progress = 0
            self._recent.append(call.fingerprint)
            return _NOT_STUCK

        self._recent.append(call.fingerprint)
        self._since_progress += 1

        verdict = (
            self._check_repeat(call)
            or self._check_alternation()
            or self._check_no_progress()
            or _NOT_STUCK
        )
        if verdict.stuck:
            self._tripped = True
            self._last = verdict
        return verdict

    def observe_all(self, calls: Iterable[ToolCall]) -> StuckVerdict:
        """Feed a whole sequence, stopping at the first stuck verdict."""
        verdict = _NOT_STUCK
        for call in calls:
            verdict = self.observe(call)
            if verdict.stuck:
                break
        return verdict

    # -- signatures ---------------------------------------------------------

    def _check_repeat(self, call: ToolCall) -> StuckVerdict | None:
        if self.repeat_threshold is None:
            return None
        count = sum(1 for item in self._recent if item == call.fingerprint)
        if count < self.repeat_threshold:
            return None
        return StuckVerdict(
            stuck=True,
            reason="repeat",
            detail=(
                f"{call.tool_name} called with identical input {count} times "
                f"within the last {len(self._recent)} calls"
            ),
            evidence=(call.fingerprint,) * count,
        )

    def _check_alternation(self) -> StuckVerdict | None:
        if self.alternation_threshold is None:
            return None
        needed = self.alternation_threshold * 2
        if len(self._recent) < needed:
            return None
        tail = list(self._recent)[-needed:]
        first, second = tail[0], tail[1]
        if first == second:
            # Not alternation; _check_repeat owns this shape.
            return None
        expected = [first if i % 2 == 0 else second for i in range(needed)]
        if tail != expected:
            return None
        return StuckVerdict(
            stuck=True,
            reason="alternation",
            detail=(
                f"two tools alternated {self.alternation_threshold} times without "
                "converging (A-B-A-B)"
            ),
            evidence=(first, second),
        )

    def _check_no_progress(self) -> StuckVerdict | None:
        if self.no_progress_threshold is None:
            return None
        if self._since_progress < self.no_progress_threshold:
            return None
        return StuckVerdict(
            stuck=True,
            reason="no_progress",
            detail=(
                f"{self._since_progress} consecutive calls mutated nothing"
            ),
            evidence=tuple(list(self._recent)[-self._since_progress :]),
        )

    _last: StuckVerdict = _NOT_STUCK


def scan(calls: Sequence[ToolCall], **kwargs: Any) -> StuckVerdict:
    """One-shot convenience wrapper over :class:`StuckDetector`."""
    return StuckDetector(**kwargs).observe_all(calls)
