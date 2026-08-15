# showwork budget-exceeded consumer-state readout r19

Date: 2026-08-15  
Status: observed / disposable local commands only  
Scope: bounded fake commands and short-lived disposable descendants; no
timeout, process-tree, receipt-schema, or public-wording change.

## Outcome matrix

| scenario | wrapper exit | receipt finish state | claims | child/descendant observation | safe interpretation |
|---|---:|---|---|---|---|
| normal command | 0 | `status=ok`, `budget_exceeded=false` | GREEN 0/0 | no descendant | wrapped command returned zero |
| nonzero child | 7 | `status=error`, `command_exit=7`, budget false | GREEN 0/0 | no descendant | child reported failure; not a proof verdict |
| wall-clock timeout | 2 | `status=budget_exceeded`, `command_exit=124`, `budget_reason=time` | GREEN 0/0 | no descendant fixture | wrapper budget expired; exit 2 is not a universal kill proof |
| RED gate | 2 | `status=ok`, `command_exit=0` | RED 0/1 | no descendant | wrapped command succeeded but `--gate` refused the unverified close |
| descendant timeout | 2 | `status=budget_exceeded`, `command_exit=124`, budget true | GREEN 0/0 | child alive immediately, self-exited within 3 seconds | timeout receipt does not prove descendant termination |

The descendant fixture used a parent that spawned a 1.5-second child and then
slept. It was bounded and cleaned up by natural exit; no unrelated process was
targeted. All roots were removed after the run.

## Consumer boundary

The wrapper exit code alone is ambiguous: both a timeout and a RED gate can be
2, while a nonzero child can be any nonzero value. Consumers must read the
finish event fields separately: `status`, `claims_verdict`, `command_exit`,
`budget_exceeded`, `budget_reason`, and any independently observed child state.
`budget_exceeded=true` means the wrapper's wall-clock budget expired. It does
not mean the proof claims passed, the child tree is gone, or the work is safe
to call complete.

## Unsupported interpretations

These fixtures do not support “all descendants terminated,” “hard real-time
completion,” “timeout means failed proof,” “exit 2 always means timeout,” or
any security, compliance, SLA, or adoption conclusion.

## owner-gated recommendation

Keep the existing event fields and document a consumer mapping that treats
wrapper outcome, proof verdict, and process observation as separate facts. Do
not add schema or process-tree behavior from this readout.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r19-full-20260815` -> **239 passed**.
