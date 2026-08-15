# showwork current-day corpus health readout

Date: 2026-08-15
Scope: read-only comparison of existing commands. No dashboard, status
vocabulary, public health claim, verifier, schema, or release change.

## Result

KEEP the existing commands. They already expose enough detail to answer the
operator question when the reader compares the whole-corpus summary with the
current date file. A single aggregate verdict is not sufficient, but no new
status surface is justified by this observation.

## Two-scope matrix

| Scope and command | Exit | Observed result | Safe interpretation |
|---|---:|---|---|
| Whole `showwork audit --json` | 3 | `YELLOW`, 394 records, 362 chained, 43 forks | Corpus contains legacy pre-chain history; not proof of current tamper |
| Current `claims-2026-08-15.jsonl` inside the same audit | 0 for the file | `GREEN`, 89/89 chained, 1 fork across 2 heads | Current-day claim ledger is intact under ordinary fork-tolerant policy |
| Current `sessions.jsonl` inside the same audit | 0 for the file | `GREEN`, 139 chained, 13 pre-chain, 23 forks | Lifecycle file has anchored legacy records and accepted branches |
| Whole `showwork audit --strict` | 2 | `RED` because three files contain forks | Strict fork policy rejects concurrency; this is not an ordinary-audit tamper result |
| `showwork verify --date 2026-08-15 --json --no-report` | 0 | `GREEN`, 63/76 active/rechecked results; 13 skipped/retracted; 0 gaps | Current claim recheck is green after excluding append-only retractions |

The current-day figures include this follow-up's own receipts, so they are a
point-in-time operator readout, not a timeless health guarantee. The hash
chain only answers the integrity question for the records it covers.

## Existing surface coverage

`showwork audit --json` exposes per-file records, chained and pre-chain counts,
forks, heads, break location, detail, and verdict. `showwork verify --date`
separately exposes current predicate results, including skipped retractions.
The combination already answers “is today healthy even though the corpus is
yellow?” when the scopes are read together.

## Decision

NO CHANGE. Keep the two-scope operator practice in internal reports. Do not
add a dashboard, new verdict name, or public health claim from this snapshot.
