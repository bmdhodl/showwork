# showwork receipt compatibility evidence matrix

Date: 2026-08-15
Scope: read-only historical command-receipt inspection and disposable reruns.
No compatibility layer, receipt rewrite, verifier relaxation, migration,
signer, public copy, legal, release, or adoption change.

## Result

KEEP the original receipts and retractions. A command receipt is compatible
with current truth only when its exact predicate and expected output still
verify. The current ledger can remain intact while old command expectations
become stale.

## Matrix

| Receipt | Original check | Provenance captured | Current isolated result | Classification |
|---|---|---|---|---|
| Packaging 12:30 | `python scripts/run_tests.py`, expected `218 passed` | Session/time/argv only; no source revision or cwd | Retracted when suite grew to 226 | Expected historical count drift |
| Packaging 12:52 | Same command, expected `226 passed` | Session/time/argv only | Retracted when suite grew to 232 | Expected historical count drift |
| Packaging 13:07 | Same command, expected `232 passed` | Session/time/argv only | Current suite exit 0, `232 passed` | Current compatible replacement |
| Fork-aware export 14:31 | Same command, expected `232 passed` | Session/time/argv only | Session verify GREEN 3/3; current suite exit 0 | Earlier date-wide observation not reproduced in isolation |
| Evidence-pack refusal 14:35 | Same command, expected `232 passed` | Session/time/argv only | Session verify GREEN 3/3; current suite exit 0 | Earlier date-wide observation not reproduced in isolation |

The command check stores no source commit, dependency lock, environment,
fixture path, or working directory. Those missing fields limit later
compatibility analysis. The `prev` hash still proves ledger continuity; it
does not prove that the command's old environment can be reconstructed.

## Current evidence

- `python scripts/run_tests.py`: exit 0, `232 passed`.
- Fresh direct pytest with a clean explicit basetemp: exit 0, `232 passed`.
- `showwork audit --json`: no `break_at` for these records; the overall
  YELLOW is legacy pre-chain history plus accepted forks.
- The earlier date-wide run that exposed three gaps is preserved as an
  observation. A fresh date-wide run exits 0 with GREEN 63/76, 13
  skipped/retracted, and zero gaps. This is not grounds to rewrite history.

## Decision

NO CHANGE. Preserve RED/retracted evidence and record new expectations in new
claims. If compatibility context becomes a recurring operator need, route an
owner-gated maintenance proposal rather than adding a silent compatibility
layer.

Reference framing: [W3C PROV constraints](https://www.w3.org/TR/prov-constraints/)
describes validity constraints for a provenance model; it does not retrofit
missing source-revision or environment fields into this ledger.
