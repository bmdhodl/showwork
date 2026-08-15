# showwork timeout copy-limit audit readout r18

Date: 2026-08-15  
Status: observed / owner-gated wording recommendation  
Scope: current README, live-enforcement wording, CLI help, implementation, and
r16/r17 disposable timeout evidence. No public copy, wrapper, process-tree,
security, compliance, or release change was made.

## Phrase/evidence matrix

| surface | phrase or behavior | classification | reason |
|---|---|---|---|
| CLI help | “halt the wrapped command after this wall-clock budget” | supported, with boundary | the option is a wall-clock timeout for the wrapped subprocess call; it is not a hard real-time promise |
| `src/showwork/cli.py` | catches `subprocess.TimeoutExpired` and records `status=budget_exceeded`, `budget_reason=time` | supported | r16 receipts observed the budget-exceeded close and retained partial receipts |
| README | “The wrapper terminates the child” | qualified | direct subprocess timeout cleanup is the implementation boundary, but r16 showed an ordinary descendant alive after the wrapper returned |
| README | “records `budget_exceeded` when the time envelope trips” | supported | the receipt state is explicit and was observed in the timeout fixtures |
| live-enforcement docs | “a killed run starts clean” | context-only | this describes clearing stuck-guard state after a trip, not universal descendant termination for `showwork run` |
| any interpretation | process-tree isolation, universal descendant kill, or hard real-time completion | unsupported | r16 parent/child/grandchild fixtures showed descendant survival; r17 design comparison retained race, permission, breakaway, and reaping limits |

## Observed process boundary

The current wrapper delegates timeout behavior to `subprocess.run(...,
timeout=...)`. In disposable r16 fixtures, the wrapper returned a timeout
receipt while a descendant remained alive immediately afterward and exited
later under its own behavior. A partial-receipt fixture retained claims and
session files. An independently exiting parent could return without a budget
exceeded state while an owned child was still alive. No unrelated process was
killed, and no real production process was targeted.

The r17 design readout compared POSIX process groups, Windows exact-PID tree
operations, Windows Job Objects, and direct parent termination. It concluded
owner-gated design-only work and explicitly refused a hard real-time or
universal daemon-kill claim.

## Bounded internal wording recommendation

> When the wall-clock budget expires, showwork records `budget_exceeded` for
> the wrapped command. The current boundary does not guarantee termination of
> descendants or hard real-time completion; a descendant may outlive the
> wrapper.

This preserves the useful receipt claim while keeping the process-tree limit
visible to human and AI readers. It is a draft for owner review, not a public
copy change in this batch.

## owner-gated decision

Keep the current implementation unchanged. Before the next public copy or
runtime release, have the owner decide whether to adopt the bounded wording and
whether a separate, cross-platform process-tree design is worth its test and
maintenance cost. Do not describe the current wrapper as a security,
compliance, SLA, or universal process-isolation mechanism.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r18-full-20260815` -> **239 passed**.
