# showwork receipt reproducibility metadata gap r9

Date: 2026-08-15  
Scope: bounded inspection of historical command receipts, session records, and
the existing compatibility/readout reports. This is report-only. No receipt
fields were added, rewritten, migrated, or re-chained.

## Result

Historical receipts preserve enough to identify an assertion and its recorded
verification outcome, but not enough to reconstruct the exact command
environment. Treat them as valid historical assertions when their recorded
chain and check are intact, not as fully reproducible build records.

## Field inventory

| Field or question | Available in the bounded evidence | Limitation | Classification |
|---|---|---|---|
| Session, timestamp, claim text, severity, check type, previous hash | Yes in `claims-2026-08-15.jsonl` | Identifies the assertion and ledger position, not all execution inputs | Preserved assertion context |
| Command argv | Yes for command checks | Arguments are present, but the invoked executable and surrounding shell state are not a complete environment record | Preserved with limits |
| Expected exit and output predicate | Sometimes: `expect_exit`, `stdout_contains` | It is a predicate, not a full captured stdout/stderr transcript | Materially limiting for replay |
| Source revision or commit | No | The historical checkout cannot be identified from the receipt alone | Materially limiting |
| Working directory | No | Relative paths and repository identity cannot be reconstructed reliably | Materially limiting |
| Python version and showwork/package version | No historical value | The current observation is Python 3.13.2, showwork 0.3.0, but that does not bind old receipts | Materially limiting |
| Environment inputs and dependency lock | No | External configuration and dependency resolution are not recoverable | Materially limiting |
| Fixture or input path | No in the command receipt | A later rerun may use an equivalent-looking but different fixture | Materially limiting |
| Session start/finish state | Partially: agent, note, status, verdict, bypass marker | No commit, cwd, or complete lifecycle graph | Helpful but incomplete |
| Evidence-pack summary | Yes: generated time, ledger counts, heads, sessions, claims, inventory | It is an export summary, not a full environment manifest | Helpful but incomplete |

## Exact evidence

The bounded sample and its interpretation are recorded in:

- `K:\showwork\.showwork\claims-2026-08-15.jsonl`
- `K:\showwork\.showwork\sessions.jsonl`
- `K:\showwork\sources\research_20260815_showwork_receipt_compatibility_evidence_matrix_r8.md`
- `K:\showwork\sources\research_20260815_showwork_proof_pack_query_answerability_r8.md`
- `<vault>\Reports\Research\showwork-receipt-compatibility-evidence-matrix-2026-08-15.md`

The compatibility sample records three historical test expectations for the
same command: `218 passed` and `226 passed` were retracted after the suite
grew, while the current `232 passed` run is the compatible replacement. The
receipt has session/time/argv evidence but no source revision or cwd. This
supports distinguishing assertion history from replay provenance.

The current observation used for this report was `Python 3.13.2`, showwork
`0.3.0`, repository commit `8a4419fb8595dfb1100a60182be01a87fe0cc360`, and a
clean working tree. These values are current evidence only; they do not repair
the missing historical fields.

## Answer boundary

The historical record can answer “what predicate was recorded, when, and what
does the current verifier make of that ledger line?” It cannot answer “which
source revision, working directory, environment, dependency resolution, or
fixture produced the original output?” without external evidence.

## Decision

KEEP the historical receipts and their retractions. NO CHANGE to the receipt
format follows from this readout. A future design discussion may consider
reproducibility metadata, but adding fields, a compatibility layer, a
migration, or a new verifier is outside this report and current scope.
