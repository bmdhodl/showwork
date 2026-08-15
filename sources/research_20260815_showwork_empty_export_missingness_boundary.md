# showwork empty-export and missingness boundary

Date: 2026-08-15
Scope: existing valid, empty, missing, RED, and unverifiable fixture behavior.
No packer, verifier, schema, public-copy, signing, legal, or release change.

## Result

KEEP the current packer and require a non-empty closed session plus an audit
verdict before a consumer treats a pack as proof. `GREEN (0/0)` is vacuous.
It must not be interpreted as evidence that an event occurred.

## Complete matrix

| Fixture/state | Audit | Claim verify | Pack | Output and safe reader label |
|---|---|---|---|---|
| Valid non-empty fixture | Exit 0, GREEN 3/3 | Exit 0, GREEN 1/1 | Exit 0, file written | `VERIFIED FOR THIS SCOPE`: one closed session and one passing claim |
| Empty date range in intact fixture | Exit 0, GREEN 3/3 | Exit 0, GREEN 0/0 | Exit 0, file written | `UNVERIFIED / EMPTY`: no sessions or claims selected |
| Missing session query | Not applicable to query | Exit 0, GREEN 0/0, empty results | Not applicable | `UNVERIFIED / MISSING`: no receipt for that session was found |
| Mismatched or stale claim | Exit 0, GREEN 3/3 | Exit 2, RED 0/1 | Exit 0, file written | `RED CLAIM`: bytes are intact but the predicate does not verify now |
| Tampered ledger | Exit 2, RED | Not trusted | Exit 2, no file | `RED CHAIN`: export refused because integrity is not established |
| Empty unverifiable tree | Exit 3, YELLOW 0/0 | Exit 0, GREEN 0/0 | Exit 0, file written | `YELLOW CHAIN + VACUOUS CLAIMS`: no proof and no event selected |

The valid and empty rows were rerun against a disposable fixture. The missing
session query returned:

```json
{"label":"session never-recorded","verdict":"GREEN","total":0,"passed":0,"results":[],"gaps":[]}
```

That is a query with no records, not a positive assertion. The prior tampered
fixture report records the RED refusal and confirms that no pack file was
written. The packer remains honest by allowing an empty export while leaving
the burden of interpretation to the consumer.

## Decision

KEEP the current packer. This is a narrow consumer-policy boundary, not a
reason to add a new verifier or status vocabulary.
