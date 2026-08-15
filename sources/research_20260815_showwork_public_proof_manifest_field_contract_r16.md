# showwork public proof-manifest field contract readout r16

Date: 2026-08-15  
Scope: disposable redacted reader table built from the existing README, SPEC,
CI documentation, evidence-pack implementation, and r14/r15 local reports.
No public schema, receipt, verifier, tracking, public-copy, authority,
compliance, adoption, signer, or release change.

## Field matrix

| candidate field | existing artifact/path | observed availability | reader risk |
|---|---|---|---|
| artifact identity | `README.md`, `SPEC.md`, `.showwork/*.jsonl`, evidence-pack heading | available as a path or named ledger | low if the path is retained; a bare pasted verdict loses identity |
| source revision | local `git rev-parse HEAD`; r14/r15 report context | available in the readout context, not in the current receipt records or public proof summary | `GREEN` can be mistaken for current source state when revision is absent |
| claim count | `showwork verify`, `scripts/evidence_pack.py` inventory | available; non-empty count is visible in the reader matrix | `GREEN (0/0)` can be misread as successful work |
| verifier command | `README.md`, `docs/ci.md`, CLI help | available as `showwork verify`, `showwork audit`, and evidence-pack commands | command without root/session/date context is not reproducible evidence |
| verdict | CLI output, audit output, evidence-pack text | available as GREEN/YELLOW/RED plus counts | a chain GREEN is not the same as a current claim GREEN |
| refusal boundary | README model, `SPEC.md`, `docs/ci.md`, r14/r15 reports | available in prose; explicit in the report matrix | omission invites authority, exact-replay, compliance, or adoption overread |

## Two unresolved cases

1. **Verified without a source revision.** A receipt can show a successful
   deterministic check against the current checkout while omitting the commit
   or source snapshot. The safe answer is “the named predicate verified against
   the observed local state on the stated date”; it is not a claim about an
   unidentified revision or exact replay.

2. **Green pack with zero claims.** The existing verifier can return `GREEN
   (0/0)` for an empty session and the evidence pack can exit successfully while
   inventorying zero claims. The safe answer is “vacuous and unproven,” not
   successful execution, current truth, adoption, authority, compliance, or
   replay.

## Minimum content-only recommendation

When a proof summary is assembled, keep six labels together: artifact identity,
observation date, source revision or explicit `revision: unavailable`, claim
count, verifier command/context, and verdict/refusal boundary. This is a
content-only reader contract. It does not justify adding a public machine schema
or modifying receipt records.

Validation: the source rows were compared without retaining private query text;
the existing r14/r15 matrices supplied the valid, mismatched, stale, tampered,
and unverifiable interpretations.

Decision: **NO CHANGE.** Keep the recommendation internal until a real reader
request or attributable comprehension evidence exists.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
