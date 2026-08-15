# Research sources: public-proof reader matrix

Date: 2026-08-15

## Fixed rubric

Every artifact is read with the same fields: chain/audit verdict, current
claim/session verdict, exit-gate close, provenance, and outside-observer or
adoption evidence. The rubric never treats a local fixture as an independent
observer.

## Matrix

| Case | Audit | Session/current state | Exit gate | Provenance | Correct reading |
| --- | --- | --- | --- | --- | --- |
| valid | GREEN, 3/3 chained | GREEN, 1/1 verified | `session.finish` status ok; exit 0 | temporary local fixture | current local claim is backed; no authorship or adoption proof |
| mismatched | GREEN, 3/3 chained | RED, 0/1; exit 2 | close was valid at assertion time, current re-check fails | local fixture; artifact changed | intact receipt, failed current-state proof; not chain tampering |
| stale | GREEN, 3/3 chained | RED, 0/1; exit 2 | close was valid at assertion time, current re-check fails | copied local receipt; current artifact changed | old receipt is stale; not external proof |
| tampered ledger | RED; exit 2 | not a success signal | evidence-pack generation refused | ledger integrity failed | altered history; do not read any GREEN subfield as success |
| unverifiable | YELLOW, 0/0; exit 3 | GREEN, 0/0; exit 0 | no close and no claims | provenance absent | vacuous and unproven; never success or adoption |

## Interpretation risks

- False positive: reading `GREEN (0/0)` as proof; reading chain GREEN as current
  truth for a mismatched artifact; reading a generated pack with an `XX` claim
  as a successful pack; reading a local fixture as an outside observer.
- False negative: treating a stale or mismatched claim as chain tampering when
  the receipt chain is intact; treating an accepted fork as a chain break when
  audit reports its heads explicitly.

The shortest safe public bundle is: raw receipt artifact, audit verdict,
non-empty session verdict, explicit exit-gate close, and provenance label. A
missing ledger or zero-claim session must be labeled unverifiable even when the
session verifier prints GREEN.

## Comparison and recommendation

Adjacent [agent-receipts](https://github.com/inchwormz/agent-receipts) uses an
explicit `unverified` state and typed trust dimensions; [Proof Agent](https://github.com/marketplace/actions/proof-agent-verify)
uses separate worker/verifier roles and PASS/FAIL/PARTIAL labels. These are
comparison signals, not showwork adoption or permission to add a verifier.

NO CHANGE to verifier or public copy. Keep the rubric as an internal review
contract. A future content change needs a real reader request or attributable
external comprehension evidence; traffic and owner fixtures do not qualify.
