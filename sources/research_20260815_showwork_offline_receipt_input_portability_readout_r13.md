# showwork offline receipt input portability readout r13

Date: 2026-08-15  
Scope: disposable copies of a two-claim local fixture. Only existing
`verify`, `audit`, and evidence-pack behavior was exercised. No receipt field,
schema, migration, signing, external service, exact-replay, authority,
compliance, adoption, or public-copy change.

## Result

Copied roots, CRLF ledger line endings, and supported normalized relative paths
remain GREEN. Reordering JSON keys changes receipt bytes and therefore breaks a
subsequent chain link; audit and evidence-pack refuse even though the claim
predicates can still evaluate GREEN. Changing the non-secret artifact label
keeps the chain GREEN but makes the predicate RED and the pack marks `XX`.

Decision: **KEEP** current portability behavior with a qualified-rerun
boundary. The receipt does not prove an identical historical environment.

## Matrix

| fixture variation | verify | audit | pack exit | pack/result | cleanup |
|---|---:|---:|---:|---|---|
| copied to another temporary root | 0 GREEN | 0 GREEN | 0 | no failed claim | removed |
| CRLF ledger line endings | 0 GREEN | 0 GREEN | 0 | no failed claim | removed |
| JSON key order changed | 0 GREEN | 2 RED | 2 | refused on chain RED | removed |
| `.` relative path (`.\\artifact.txt`) | 0 GREEN | 0 GREEN | 0 | no failed claim | removed |
| parent-relative path (`subdir/../artifact.txt`) | 0 GREEN | 0 GREEN | 0 | no failed claim | removed |
| non-secret fixture label changed | 2 RED | 0 GREEN | 0 | `XX` failed claim | removed |

The JSON-order result is a byte-level chain-integrity refusal, not evidence
that JSON objects are semantically different to the claim checker. The label
result is a current predicate failure, not a historical replay verdict.

