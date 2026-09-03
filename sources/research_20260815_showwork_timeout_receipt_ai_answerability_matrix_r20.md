# showwork r20: timeout receipt AI answerability matrix

Date: 2026-08-15  
Scope: redacted local receipt dictionaries and a deterministic classifier. No model call, receipt-schema change, CLI change, exit-code change, or process-tree action was performed.

## Field-combination matrix

| case | key fields | answer class | decision | unsupported inference |
|---|---|---|---|---|
| complete | `ok`, `GREEN`, exit 0, budget false | verified success | answer | adoption, current external truth |
| timeout with unknown child | `budget_exceeded`, `GREEN`, exit 124, budget true | budget exceeded | qualify | descendant termination, successful completion |
| RED gate | `ok`, `RED`, exit 0, budget false | proof refusal | refuse | successful completion, adoption |
| nonzero child | `error`, `GREEN`, exit 7, budget false | command error | refuse | successful completion, claims acceptance |
| partial | missing `claims_verdict` and `command_exit` | unknown | refuse | completion, descendant termination |
| `ok` plus budget true | contradictory fields | contradictory | refuse | completion, descendant termination |
| timeout plus exit 0 | contradictory fields | contradictory | refuse | completion, descendant termination |
| `error` plus exit 0 | insufficiently interpretable | unknown | refuse | completion, descendant termination |

The matrix is fail-closed. `claims_verdict=GREEN` cannot override a nonzero wrapped-command exit, a budget contradiction, a missing required field, or an unknown descendant state. A timeout receipt can answer that the wrapper budget expired, but it cannot answer whether every descendant stopped or whether the claimed work completed.

## Boundary and recommendation

The safe consumer contract is to separate answer, qualify, unknown, and refuse. An **owner-gated** copy/evaluator review may expose these classes using fields already emitted by a receipt. It must preserve the distinction between wrapper timeout and descendant termination uncertainty.

No new field, verifier, signer, schema, model integration, process-tree policy, adoption claim, or exact-replay claim is supported by this readout.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r20-full-20260815` -> **239 passed**
