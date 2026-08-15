# showwork run wall-clock budget boundary readout r15

Date: 2026-08-15  
Scope: disposable child commands through the existing `showwork run
--max-seconds` wrapper. No real agent, network, budget API, verifier, schema,
signer, authority, compliance, adoption, exact-replay, public-copy, or release
change.

## Boundary matrix

| child | limit | wrapper exit | finish state | budget evidence | observed wall time |
|---|---:|---:|---|---|---:|
| `python -c "print('ok')"` | 2.0s | 0 | `ok`, child 0 | `budget_exceeded=false` | 0.167s |
| `python -c "import time; time.sleep(0.35)"` | 1.0s | 0 | `ok`, child 0 | false | 0.513s |
| `python -c "import sys; sys.exit(7)"` | 2.0s | 7 | `error`, child 7 | false | 0.160s |
| `python -c "import time; time.sleep(1.0)"` | 0.2s | 2 | `budget_exceeded`, child 124 | true, reason `time` | 0.314s |
| child writes `partial.txt`, records a passing claim, then sleeps 1.0s | 0.2s | 2 | `budget_exceeded`, child 124 | true, partial claim retained | 0.326s |

The timeout rows recorded a durable `session.finish` with
`budget_exceeded=true`, `budget_reason=time`, and the wrapper's exit `2`.
The wrapper's observed wall time exceeded the nominal limit by roughly 0.1s in
these Windows runs, which is expected process-termination overhead rather than
a hard real-time guarantee. Temporary roots and child files were removed after
each case.

## Exact command shape

Each case used:

```text
python -m showwork.cli --root <temporary-root> run --session <case> --agent codex --max-seconds <limit> -- python -c <child-code>
```

The partial case used `-- python partial.py` and recorded its claim before the
timeout. A budget-exceeded close is not a clean successful run, even when its
partial claim currently verifies.

## Decision

**NO CHANGE.** Keep the wrapper as a coarse wall-clock envelope and document
the termination/receipt semantics. Do not call it a process-tree supervisor or
hard real-time timer.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r15-full-20260815` -> **234 passed in 13.27s**.
