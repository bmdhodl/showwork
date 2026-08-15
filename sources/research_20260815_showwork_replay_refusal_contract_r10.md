# showwork replay/refusal contract r10

Date: 2026-08-15  
Scope: historical command receipts, current disposable examples, and the r9
metadata-gap report. This is wording research only. No fields were added, no
history was rewritten, and no compatibility layer or verifier was introduced.

## Result

Separate three statements: a receipt can preserve an assertion, it can carry
enough context for a qualified rerun, or it can support a refusal to claim
exact replay. Missing source revision, cwd, environment, dependency lock, and
fixture path make the historical receipt assertion-only for exact replay.

## Replay matrix

| Metadata state | Safe answer | Required qualifier | Refusal wording |
|---|---|---|---|
| Complete declared replay context | “The receipt contains the recorded argv, expected output predicate, source revision, cwd, runtime/dependency context, environment inputs, and fixture identity needed for a qualified rerun.” | A rerun checks current reality and may differ from the original external state; metadata presence is not a guarantee of identical results. | “Exact historical execution is proven” remains too strong unless the external inputs and toolchain are independently controlled. |
| Partial context, matching current command | “The historical assertion and current check are comparable at the recorded predicate level.” | State which fields are missing and identify the current checkout/runtime used for the comparison. | “This exact historical run was reproduced” or “the same environment was used.” |
| Current showwork receipt shape | “The receipt records session, time, claim, check, argv, and sometimes expected exit/output predicates.” | It omits historical source revision, cwd, Python/package version, environment, dependency lock, and fixture path. | “The original build/run can be reconstructed from this receipt.” |
| No replay context beyond assertion/chain | “A claim was recorded at the stated time and its ledger integrity can be assessed.” | This says nothing about the original execution inputs or external state. | “The command can be replayed,” “the output is reproducible,” or “the result is equivalent.” |
| Historical comparison across suite growth | “The older expectation is a point-in-time assertion; a later result may be a compatible replacement.” | Preserve retraction and explain changed counts, as with `218 passed`, `226 passed`, and `232 passed`. | “The old receipt was tampered with” solely because current output differs. |

## Exact evidence

The bounded receipt inventory is in:

- `K:\showwork\sources\research_20260815_showwork_receipt_reproducibility_metadata_gap_r9.md`
- `K:\showwork\sources\research_20260815_showwork_receipt_compatibility_evidence_matrix_r8.md`
- `K:\showwork\.showwork\claims-2026-08-15.jsonl`
- `K:\showwork\.showwork\sessions.jsonl`
- `C:\Users\patri\Documents\Obsidian Vault\Reports\Research\showwork-receipt-reproducibility-metadata-gap-2026-08-15.md`

The compatibility evidence contains session/time/argv and expected predicates
for historical test counts. It does not bind those records to a source commit,
working directory, Python or package version, environment inputs, dependency
lock, or fixture path. Current Python 3.13.2, showwork 0.3.0, and commit
`8a4419fb8595dfb1100a60182be01a87fe0cc360` are present-day observations only.

The [W3C PROV constraints](https://www.w3.org/TR/prov-constraints/) provide a
useful provenance comparison, but vocabulary does not fill omitted execution
metadata and does not prove replay.

## Decision

KEEP the assertion-versus-replay boundary and the refusal wording. NO CHANGE
to receipt format, schema, migration, re-chain, verifier, public copy, or
release process.
