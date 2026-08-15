# showwork child-timeout/descendant boundary readout r16

Date: 2026-08-15  
Scope: disposable local Windows process fixtures. The implementation and
existing timeout tests were inspected first: `src/showwork/cli.py` uses
`subprocess.run(..., timeout=...)`, records `budget_exceeded`, and returns 2;
the tests cover the wrapper timeout and receipt fields. No process policy or
production code changed.

## Case matrix

Each wrapper used `--max-seconds 0.15`. Descendants had their standard streams
detached so the wrapper's return could be observed without waiting for the
child's handles. Child liveness was checked with an exact owned PID using
`tasklist`, then after a 1.7-second bounded grace period. Children self-exited;
no unrelated process was killed.

| case | wrapper exit/status | receipt files | child immediately after wrapper | child after grace | cleanup |
|---|---|---|---|---|---|
| parent-only sleep | 2 / `budget_exceeded`, reason `time` | `sessions.jsonl` | none | none | clean |
| descendant outlives parent | 2 / `budget_exceeded`, reason `time` | `sessions.jsonl` | alive | dead | clean |
| partial receipt + descendant | 2 / `budget_exceeded`, reason `time` | `claims-2026-08-15.jsonl`, `sessions.jsonl` | alive | dead | clean |
| parent exits independently while child continues | 0 / `ok`, budget false | `sessions.jsonl` | alive | dead | clean |

The timeout cases returned in about 0.26-0.28 seconds on this run, above the
0.15-second budget because the wrapper and OS scheduling add overhead. The
partial case retained the claim receipt while the wrapper recorded its own
budget-exceeded finish. The independent-parent case demonstrates that a clean
wrapper exit does not establish that a child is already gone.

## Interpretation

The current wrapper provides a bounded parent-process wait and durable budget
receipt. It does not establish hard process-tree termination or hard real-time
behavior. A future repair would need an explicit, platform-reviewed process
group/tree design and tests; this readout does not authorize one.

Decision: **NO CHANGE.** Preserve the current wording and its limits. Do not
claim descendant isolation, hard real-time enforcement, or complete stop of all
work from the observed timeout.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
