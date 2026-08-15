# showwork proof-manifest AI answerability readout r15

Date: 2026-08-15  
Scope: a disposable six-row reader manifest assembled from existing README,
SPEC, CI, evidence-pack, and r14 report artifacts. The manifest was not
committed. No receipt format, public schema, crawler tracking, public copy,
verifier, authority, compliance, adoption, signer, or release change.

## Coverage

All 6/6 rows carried the required fields: question, evidence artifact,
command, observed state, safe answer, and refusal boundary.

| question | evidence | observed state | safe answer | refusal boundary |
|---|---|---|---|---|
| What does a valid proof support? | README, SPEC, receipt | qualified local proof | declared predicate checked against named local state | no authorship/adoption |
| What does a failed claim mean? | r14 exit taxonomy | current predicate failed | claim is not backed now | not automatically chain tampering |
| What does chain tampering mean? | SPEC, evidence pack | chain RED / pack refused | retention integrity is unavailable | not current truth when chain is intact |
| What does empty or zero-claim output mean? | r14 zero-claim report | vacuous/unproven | no non-empty claim evidence | not successful run/adoption |
| Can an older proof be called current? | r14 age/revision report | qualified by age/revision | state observation date and revision | not exact replay |
| Does showwork prove adoption or compliance? | README and pack disclaimer | refused | no such evidence in these artifacts | no adoption/authority/compliance claim |

## Gaps

Two questions remain deliberately ambiguous without more context: what “verified”
means when source revision is absent, and what a green pack means when it has no
claims. There is no single public machine-readable manifest; the rows point to
existing files and commands. A page being answerable is not evidence that the
underlying claim is true or adopted.

## Recommendation

**REPAIR-DESIGN-ONLY.** If real reader confusion is observed, consider a small
internal answer map linking each question to the current artifact and refusal
boundary. Do not publish a new schema, make the map an authority, or edit public
copy from this synthetic readout.

Canonical local evidence: `K:\showwork\sources\research_20260815_showwork_proof_bundle_ai_answerability_boundary_r13.md` and the r14 reader reports.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r15-full-20260815` -> **234 passed in 13.27s**.
