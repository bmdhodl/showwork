# showwork historical command-receipt drift

Date: 2026-08-15
Scope: read-only classification of preserved command receipts. No receipt
rewrite, destructive rerun, verifier/schema, signing, public-copy, legal, or
release change.

## Result

REPAIR-REPORT-ONLY. Historical command receipts can become stale as the test
suite grows. That is different from a broken ledger chain. Preserve the old
claims and retractions, use a new claim for a new test count, and do not turn a
historical failure into a current GREEN claim.

## Evidence

The original records all use the same command shape, `python scripts/run_tests.py`,
but different expected output:

| Session and time | Expected output | Current status | Classification |
|---|---|---|---|
| `release-packaging-metadata`, 12:30 | `218 passed` | Append-only retraction says the suite grew to 226 | Historical count drift |
| `release-packaging-metadata`, 12:52 | `226 passed` | Append-only retraction says the suite grew to 232 | Historical count drift |
| `release-packaging-metadata`, 13:07 | `232 passed` | Current session recheck passes | Repaired evidence, still historical |
| `fork-aware-receipt-export`, 14:31 | `232 passed` | Isolated session recheck `GREEN 3/3`; current suite passes | Earlier date-wide failure was not reproducible in isolation |
| `evidence-pack-red-refusal`, 14:35 | `232 passed` | Isolated session recheck `GREEN 3/3`; current suite passes | Earlier date-wide failure was not reproducible in isolation |

The earlier date-bounded loop observed three gaps while executing the full
day's command-backed claims. A fresh date-bounded recheck now exits 0 with
`GREEN`, 63/76 results, 13 skipped/retracted, and zero gaps. The isolated
session rechecks for the fork-aware and evidence-pack rows also pass. This
change in observation does not alter ledger bytes; it demonstrates that a
date-wide command evaluation can include historical context and execution
load that an isolated session recheck does not.

The repository's current clean-basetemp suite is `232 passed`. The ledger
audit remains chain-valid apart from its known legacy YELLOW and accepted
forks. No `break_at` or tamper result is associated with these claims.

## Classification rule

- A changed expected test count with an explicit retraction is **historical
  command drift**, not ledger corruption.
- A current command that fails in an isolated, reproducible fixture is a
  **current proof gap** and must remain RED.
- A date-wide failure that is not reproducible by session-scoped verification
  is an **evaluation-context observation**, not evidence for a verifier or
  source rewrite.

## Decision

REPAIR-REPORT-ONLY. Keep old receipts and retractions. If the date-wide
evaluation context becomes a recurring operator problem, open a separate
owner-gated maintenance card; do not rewrite history in this pass.
