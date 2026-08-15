# showwork verifier exit taxonomy readout r14

Date: 2026-08-15  
Scope: existing `audit`, session `verify`, `finish`, and evidence-pack exits on
synthetic local roots. No exit-code change, verifier, schema, signing,
authority, compliance, adoption, exact-replay, public-copy, or release change.

## Exit/state matrix

All positive fixtures were closed with the existing `finish --status ok` gate
at setup time, exit `0`. The stale, mismatched, and tampered rows then mutated
the copied root after that close, so their original finish remains historical
and is not rerun as a new success.

| state | audit | verify | pack | reader state |
|---|---:|---:|---:|---|
| valid | 0 GREEN, 3/3 chained | 0 GREEN, 1/1 | 0 | current local observation |
| stale current artifact | 0 GREEN, 3/3 chained | 2 RED, 0/1 | 0 with failed claim row | receipt chain intact, predicate stale/mismatched |
| mismatched receipt predicate | 0 GREEN, 3/3 chained | 2 RED, 0/1 | 0 with failed claim row | receipt bytes are chain-valid, declared check fails |
| tampered historical ledger line | 2 RED | 0 GREEN, 1/1 | 2 refused | chain failure; do not read verify GREEN alone as proof |
| empty root | 3 YELLOW, no ledger | 0 GREEN, 0/0 | 0 with YELLOW 0/0 pack | vacuous and unproven |
| missing root ledger | 3 YELLOW, no ledger | 0 GREEN, 0/0 | 0 with YELLOW 0/0 pack | unavailable and unproven |

The tampered row demonstrates why the checks must be read together: changing a
session record made `audit` RED while the unchanged claim still made session
`verify` GREEN. The evidence pack refuses when the chain is RED. Conversely,
stale and mismatched rows keep chain integrity GREEN while `verify` catches the
current-state failure.

## Finish boundary

`finish --status ok` returned exit `0` only for the valid and zero-claim setup
roots after their own claims were evaluated. It is a close-time observation,
not a guarantee that a later mutation will still verify. A reader must pair the
close event with a fresh audit and current-state verification.

## Recommendation

**NO CHANGE.** Keep the existing exit codes and publish the interpretation
matrix only as an internal reading aid. The explicit rule remains:
`GREEN (0/0)` is vacuous when no non-empty closed claim set exists.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r14-full-20260815` -> **234 passed in 11.67s**.
