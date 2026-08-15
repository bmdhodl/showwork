# Research sources: fork-aware receipt export

Date: 2026-08-15

## Existing paths inspected

- `src/showwork/audit.py`: audit JSON includes per-file `forks`, `heads`,
  `head`, `break_at`, `detail`, and `verdict`.
- `scripts/evidence_pack.py`: the generated pack includes chain verdict,
  per-file records/chained/pre-chain/head prefix, activity counts, and a
  receipt inventory with timestamp, session, claim, check type, and current
  verification mark.
- `docs/compliance.md` and `README.md`: the public boundary says fork heads
  are visible to the auditor and the pack is supporting evidence, not a
  certification.

## Read-only observations

The current local repository audit is `YELLOW`: `total_records: 340`,
`total_chained: 308`, and `total_forks: 41`. `sessions.jsonl` has 128 records,
115 chained, 13 pre-chain records,
22 forks, and 34 branch heads. The existing export pack does not serialize the
fork count or branch-head list, source checkout, commit, agent, or explicit
missing-provenance label. It shows only the ledger directory name `.showwork`
and session identity in the receipt inventory.

A temporary fork fixture built from the existing
`tests.test_audit._union_merge_fork` shape produced a `GREEN` audit with 7/7
records chained and 1 fork across 2 branch heads. `build_pack` returned code 0
and rendered a `GREEN (7/7)` chain summary, 2 active sessions, 1/1 verified
claim, 0 refusals, 0 bypasses, and one receipt row for `export-case`.

## Recommendation

NO PRODUCT CHANGE in this pass. Keep fork-tolerant audit behavior, but treat a
forked export as owner-local evidence unless its consumer also receives the
underlying audit JSON and independent source/provenance context. Do not count
forks as adoption or endorsement. If a public fork export is later requested,
make that a separate narrow contract decision for explicit fork-head and
source provenance fields; do not infer them from the current pack.
