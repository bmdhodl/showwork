# showwork verification scale/performance readout r16

Date: 2026-08-15  
Scope: disposable local synthetic ledgers only. Four sizes, five repetitions
per operation. No production ledger, implementation change, public benchmark,
throughput promise, or SLA claim.

## Fixture and method

Each root contained one artifact, `size` valid `file_exists` claims in one
session, ten retraction records, and a sessions ledger with one accepted
concurrent fork (two branch records re-anchored to the same parent). The
measurement called `audit_root`, `verify_session`, `verify_date`, and
`scripts.evidence_pack.build_pack` directly. Timings are wall-clock milliseconds
on this Windows checkout. The reported memory number is Python
`tracemalloc` peak allocation, not process RSS; Windows process memory was not
measured. Medians and min/max ranges use five runs.

| claims | ledger bytes | audit median/range ms | session verify median/range ms | date verify median/range ms | pack median/range ms |
|---:|---:|---:|---:|---:|---:|
| 10 | 5,675 | 1.016 / 1.005-9.962 | 0.978 / 0.970-1.196 | 1.165 / 1.100-1.234 | 2.674 / 2.557-2.963 |
| 100 | 27,486 | 2.740 / 2.620-11.961 | 26.656 / 26.619-27.761 | 26.143 / 25.778-27.119 | 29.062 / 28.615-29.669 |
| 500 | 124,286 | 9.673 / 9.465-19.014 | 138.225 / 137.397-141.660 | 137.647 / 134.068-144.399 | 146.169 / 143.782-150.158 |
| 1,000 | 246,307 | 19.177 / 18.510-27.667 | 274.830 / 271.704-338.129 | 273.712 / 273.060-291.650 | 292.311 / 290.821-478.354 |

All valid fixtures audited and verified GREEN; the evidence pack returned code
0. The largest observed Python allocation peaks were approximately 841 KiB for
audit, 1,811 KiB for session/date verification, and 2,782 KiB for evidence
pack generation. These are implementation-local observations, not capacity
limits.

## Refusal behavior

A separate disposable ledger with one malformed JSONL line audited RED and
`evidence_pack` returned code 2 with the refusal that a RED chain cannot produce
evidence. The fixture was deleted after the readout; no production receipt was
used.

## Decision

**NO CHANGE.** The small synthetic sample shows roughly linear growth in this
range and identifies session/date verification as the larger measured cost, but
it is too narrow to generalize. Keep performance questions as future bounded
research; do not publish a benchmark or promise throughput/SLA behavior.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
