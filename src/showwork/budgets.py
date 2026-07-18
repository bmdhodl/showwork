"""Run budgets: wall-clock, tool-call count, and per-tool rate.

The dimensions here are deliberately the ones the platform does NOT give away.
Anthropic's gateway and Cloudflare AI Gateway both enforce spend in dollars, so
building another dollar cap would be rebuilding a free feature. Neither of them
caps *wall-clock time* or *tool-call count* for a single run, because neither
can see a run — they see a stream of independent requests.

An agent that has made 400 tool calls in one task is out of control whether or
not it has spent $4 or $400. That is the thing worth capping here.

Time is injected rather than read from the clock directly, so budgets are
testable without sleeping and deterministic under replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

__all__ = [
    "BudgetVerdict",
    "RunBudget",
]


@dataclass(frozen=True)
class BudgetVerdict:
    """Result of checking a run against its budget."""

    exceeded: bool
    reason: str = ""
    detail: str = ""

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return self.exceeded

    def as_dict(self) -> dict:
        return {
            "exceeded": self.exceeded,
            "reason": self.reason,
            "detail": self.detail,
        }


_WITHIN = BudgetVerdict(exceeded=False)


@dataclass
class RunBudget:
    """A ceiling on one agent run.

    Any limit left as ``None`` is not enforced. All limits are inclusive
    ceilings: ``max_tool_calls=50`` trips on the 51st call, not the 50th, so a
    budget of N permits exactly N calls.

    ``clock`` returns monotonic seconds. It is injectable so tests and replays
    do not depend on real time.
    """

    max_seconds: float | None = None
    max_tool_calls: int | None = None
    max_calls_per_tool: dict[str, int] | None = None
    clock: Callable[[], float] = field(default=None, repr=False)  # type: ignore[assignment]

    _started: float | None = field(default=None, init=False, repr=False)
    _calls: int = field(default=0, init=False, repr=False)
    _per_tool: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _tripped: BudgetVerdict | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_seconds is not None and self.max_seconds <= 0:
            raise ValueError("max_seconds must be > 0, or None to disable")
        if self.max_tool_calls is not None and self.max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1, or None to disable")
        if self.max_calls_per_tool:
            for tool, limit in self.max_calls_per_tool.items():
                if limit < 1:
                    raise ValueError(f"max_calls_per_tool[{tool!r}] must be >= 1")
        if self.clock is None:
            import time

            self.clock = time.monotonic

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Begin the run. Idempotent; the first call wins."""
        if self._started is None:
            self._started = self.clock()

    @property
    def elapsed(self) -> float:
        if self._started is None:
            return 0.0
        return self.clock() - self._started

    @property
    def calls(self) -> int:
        return self._calls

    def reset(self) -> None:
        self._started = None
        self._calls = 0
        self._per_tool.clear()
        self._tripped = None

    # -- enforcement --------------------------------------------------------

    def check(self) -> BudgetVerdict:
        """Check time only, without recording a call.

        Useful from a periodic hook: a run can blow its wall-clock budget while
        blocked on a single very slow tool call, and a purely call-driven check
        would never notice.
        """
        if self._tripped is not None:
            return self._tripped
        verdict = self._check_time() or _WITHIN
        if verdict.exceeded:
            self._tripped = verdict
        return verdict

    def record(self, tool_name: str = "") -> BudgetVerdict:
        """Record one tool call and return the resulting verdict.

        Latches: once exceeded, later calls return the same verdict until
        :meth:`reset`.
        """
        if self._tripped is not None:
            return self._tripped

        self.start()
        self._calls += 1
        if tool_name:
            self._per_tool[tool_name] = self._per_tool.get(tool_name, 0) + 1

        verdict = (
            self._check_time()
            or self._check_total()
            or self._check_per_tool(tool_name)
            or _WITHIN
        )
        if verdict.exceeded:
            self._tripped = verdict
        return verdict

    def _check_time(self) -> BudgetVerdict | None:
        if self.max_seconds is None or self._started is None:
            return None
        elapsed = self.elapsed
        if elapsed <= self.max_seconds:
            return None
        return BudgetVerdict(
            exceeded=True,
            reason="time",
            detail=f"run exceeded {self.max_seconds:g}s wall clock ({elapsed:.1f}s elapsed)",
        )

    def _check_total(self) -> BudgetVerdict | None:
        if self.max_tool_calls is None or self._calls <= self.max_tool_calls:
            return None
        return BudgetVerdict(
            exceeded=True,
            reason="tool_calls",
            detail=f"run exceeded {self.max_tool_calls} tool calls ({self._calls} made)",
        )

    def _check_per_tool(self, tool_name: str) -> BudgetVerdict | None:
        if not self.max_calls_per_tool or not tool_name:
            return None
        limit = self.max_calls_per_tool.get(tool_name)
        if limit is None:
            return None
        used = self._per_tool.get(tool_name, 0)
        if used <= limit:
            return None
        return BudgetVerdict(
            exceeded=True,
            reason="tool_rate",
            detail=f"{tool_name} exceeded {limit} calls ({used} made)",
        )
