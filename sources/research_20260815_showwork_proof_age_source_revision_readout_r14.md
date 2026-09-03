# showwork proof age and source revision readout r14

Date: 2026-08-15  
Scope: a fixed local set of README/specification, receipt, package, and prior
research artifacts. No receipt fields, schema, history rewrite, verifier,
public-copy, exact-replay, reproducibility, adoption, authority, compliance,
signer, or release change.

## Observed context

The current checkout was `a9bde9f167729260461af941aee9cc5111b06ccd` at the
time of the readout, and `src/showwork/__init__.py` reports package version
`0.3.1`. The synthetic current receipt had embedded record timestamps and
passed the current local audit and predicate check. Those observations do not
make older artifacts current or replayable.

## Age and revision matrix

| artifact | recorded age/source context | current-state check | missingness | safe classification |
|---|---|---|---|---|
| `README.md` | no `recorded_at`, source revision, or package version in the artifact | documentation only | timestamp, revision, package version | historical assertion or unqualified description |
| `SPEC.md` | no `recorded_at`, source revision, or package version in the artifact | contract text only | timestamp, revision, package version | historical assertion or unqualified description |
| `.showwork/claims-*.jsonl` + `sessions.jsonl` | timestamps embedded in records; no source revision/package version | `audit` and session `verify` can be run against the current checkout | source revision and package version | current local observation when checked now |
| r13 package-provenance crosswalk | report dated 2026-08-15; source context recorded as `697b8a9`; candidate package `showwork-0.3.1` | explicitly not an exact replay; current checkout is `a9bde9f` | current-state verification at report time | historical assertion |

The r13 report's revision and the current checkout differ. That is not a
contradiction: it is evidence that a proof reader must keep the source revision
visible when comparing a historical report with today's tree.

## Safe reader wording

Use wording of this shape for a checked local artifact:

> Observed on 2026-08-15 in source revision `a9bde9f`, package version `0.3.1`;
> the receipt chain and declared predicate were checked against this local
> checkout.

If revision or package context is absent, say that the artifact is historical
or unqualified. Do not say “same build,” “exact replay,” “current everywhere,”
or “verified by an outside observer.”

## Decision

**REPAIR-DESIGN-ONLY.** Keep receipt format unchanged. A future owner-approved
reader may expose age/revision metadata beside a proof artifact, but this card
does not add fields, rewrite old receipts, or change public copy.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r14-full-20260815` -> **234 passed in 11.67s**.
