# showwork qualified rerun context contract r12

Date: 2026-08-15  
Scope: read-only design contract derived from the r11 replay-context matrix.
No receipt field, schema, migration, verifier behavior, public copy, signer,
authority, compliance, adoption, exact-replay, or reproducibility claim was
added.

## Result

Optional context could make a future predicate rerun more interpretable, but
the current receipt only proves the recorded assertion and its check against
the current project state. The safe claim remains **qualified rerun** or
**predicate comparison**, never exact historical replay.

Decision: **REPAIR-DESIGN-ONLY**. Keep the current receipt format and design
tests before considering any future optional metadata.

## Field contract

| context | presence/redaction contract | wording supported | wording refused |
|---|---|---|---|
| command argv and expected predicate | existing command-check fields; redact secrets and sensitive arguments | “the recorded predicate can be rerun” | “the historical command ran with identical inputs” |
| source revision | optional commit or immutable revision identifier | “rerun against the recorded revision” | “the current tree is the historical tree” when absent or changed |
| project identity and working directory | normalized project label or relative root; never require raw private paths | “the rerun used the named project context” | “the same filesystem context was reproduced” |
| runtime and package version | interpreter and showwork/package versions | “the rerun used the recorded runtime/package versions” | “all runtime behavior is identical” |
| dependency identity | lockfile or dependency digest, without credentials | “dependency context was recorded” | “external dependencies were unchanged” when not captured |
| fixture/input identity | privacy-safe label or digest; no raw private payload | “the named fixture was compared” | “the external inputs were identical” |
| environment inputs | names and redacted/hashed values only; no secrets | “relevant environment context was recorded” | “the environment was fully reproduced” |
| external service/input snapshot | explicit snapshot identifier or refusal when missing | “the captured snapshot was compared” | “the external service returned the same historical state” |

## Refusal matrix

| situation | allowed readout | required refusal |
|---|---|---|
| all local context present, no external dependency | qualified rerun and predicate comparison | exact historical reproduction |
| source revision missing or changed | current-state predicate result | same-code claim |
| fixture is redacted or only a digest remains | fixture identity comparison | identical-input claim |
| dependency lock differs | rerun with changed dependency context | unchanged dependency claim |
| external service has no retained snapshot | local rerun with missing-context note | identical external-state claim |
| current verifier or suite changed | current verifier result plus drift note | historical verifier result reproduced |

## Compatibility and privacy tests

Any future implementation would need tests for absent fields, unknown fields,
redacted values, changed revision, changed dependency digest, changed fixture
identity, and changed verifier version. Optional context must not become
required for old receipts, and raw paths, environment values, credentials, or
external payloads must not be copied into the ledger.

## Boundary

Current wording: “The receipt records the assertion and its predicate; the
chain and current verifier can be checked.”

Candidate wording: “The receipt includes context for a qualified rerun of this
predicate, with the listed revision/runtime/fixture identifiers.”

Forbidden wording: “the exact historical run was reproduced,” “the external
inputs were identical,” “the result is permanently true,” or “the receipt is
fully reproducible.”

