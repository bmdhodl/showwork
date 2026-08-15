# showwork scope-state answer contract

Date: 2026-08-15
Scope: deterministic interpretation rules over disposable local packs. No
exit-code, status vocabulary, verifier, schema, public-copy, legal,
compliance, human-attestation, release, or adoption change.

## Result

KEEP the current outputs and use a narrow reader contract. Technical GREEN is
not human approval, legal compliance, or adoption. The answer must name the
scope, whether it contains records, and whether the chain and claims verify.

## State matrix

| State | Exact local evidence | Minimum safe answer | Required qualifier | Forbidden overclaim |
|---|---|---|---|---|
| Valid non-empty | Audit GREEN 3/3; verify GREEN 1/1; pack written | “This bounded pack contains one claim that verifies at export.” | Date range, check type, and export-time qualifier | “Everything happened” or “compliant” |
| Empty range | Intact pack with 0 sessions and `GREEN (0/0)` claims | “No records were selected for this range.” | Empty is vacuous and unproven | “The event was verified” |
| Missing session | `verify --session never-recorded` exit 0, GREEN 0/0, no results | “No receipt for that session was found.” | Search miss is not a negative event proof | “The session did not happen” or “passed” |
| Stale/mismatched claim | Chain GREEN 3/3; verify RED 0/1 exit 2; pack written with `XX` | “The bytes are intact, but this predicate does not verify now.” | Point-in-time assertion may differ from current state | “The ledger was tampered” or “the task succeeded” |
| Tampered chain | Audit RED exit 2; pack exit 2 and no file | “Refused: chain integrity is not established.” | Treat the artifact as unusable proof | “The pack proves the event” |
| Empty unverifiable tree | Audit YELLOW 0/0 exit 3; verify GREEN 0/0; pack writes YELLOW | “No proof is available in this empty/unverifiable scope.” | Chain and claim verdicts are different signals | “GREEN means verified” |
| Bypassed close | Pack shows one verification bypass and an `XX` claim | “A bypass was recorded; the failing claim remains visible.” | Bypass authorization is not in the receipt | “A human approved the bypass” |

## Provenance and authority boundary

The [W3C PROV primer](https://www.w3.org/TR/prov-primer/) models provenance
through entities, activities, agents, responsibility, usage, generation, and
time. The current pack exposes some time, claim, session, and chain material,
but it is not a PROV interchange graph and does not authenticate its free-form
agent label. That comparison is a vocabulary aid only.

## Decision

NO CHANGE. Keep the existing commands and apply this answer/refusal contract
to local or AI interpretation. Do not add a status value or public wording.
