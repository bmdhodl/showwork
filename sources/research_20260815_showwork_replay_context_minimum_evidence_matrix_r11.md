# showwork replay-context minimum evidence matrix r11

Date: 2026-08-15  
Scope: read-only ranking of context that could make a future rerun more useful.
No receipt schema, verifier, migration, public copy, signer, authority,
compliance, adoption, or exact-reproduction claim was added.

## Result

The smallest useful future context bundle is optional design material, not a
current receipt contract: source revision, working directory, runtime/package
version, dependency identity, fixture identity, argv, and expected predicate.
Even that bundle would support only a qualified rerun. It would not prove that
the historical external inputs or result were reproduced exactly.

## Current evidence

The current claim record shape is defined at `SPEC.md:39-59` and written by
`src/showwork/ledger.py:276-285`: session, timestamp, claim, severity, optional
artifact, and optional check. Command checks may retain argv and expected
predicates, but the evidence pack inventory at
`scripts/evidence_pack.py:115-199` renders timestamp, session, claim, check,
and current verification result. It does not render source revision, cwd,
runtime, dependency, environment, or fixture identity.

## Ranked matrix

| Context | Current presence | Replay value | Privacy/storage risk | Compatibility impact |
|---|---|---|---|---|
| Command argv | Present for command checks | High | Low, except arguments may contain paths/secrets | Low; existing field |
| Expected exit/output predicate | Sometimes present | High for predicate comparison | Low | Low; existing field |
| Source revision/commit | Absent historically | Very high for code identity | Low | Medium if added later |
| Working directory/project identity | Absent | High for relative paths | Medium; may expose local paths | Medium |
| Python/showwork/package version | Absent historically | High for interpreter behavior | Low | Low/medium |
| Dependency lock or package digest | Absent | High for deterministic setup | Low/medium | Medium |
| Fixture/input path or identity | Absent | High for local replay | High; paths may reveal private data | Medium/high |
| Environment inputs | Absent | High when checks depend on configuration | High; values must never be copied raw | High |
| External service/input snapshot | Absent | Very high in theory | High and often impossible to retain | High; outside current local-proof scope |

## Safe boundary

Current: “The receipt records the assertion and its predicate; the chain and
current verifier can be checked.”

Possible future design wording: “The receipt includes context for a qualified
rerun of this predicate, with the listed revision/runtime/fixture identifiers.”

Still forbidden: “The exact historical run was reproduced,” “the external
inputs were identical,” “the result is permanently true,” or “the receipt is
fully reproducible.”

Evidence paths:

- `K:\showwork\sources\research_20260815_showwork_receipt_reproducibility_metadata_gap_r9.md`
- `K:\showwork\sources\research_20260815_showwork_replay_refusal_contract_r10.md`
- `K:\showwork\SPEC.md`
- `K:\showwork\scripts\evidence_pack.py`

## Decision

REPAIR-DESIGN-ONLY. Keep the current receipt format. If replay context is
revisited, design privacy-safe optional metadata and compatibility tests first;
do not implement it or claim reproducibility from this matrix.
