# Spec-version reader compatibility matrix — r26

Date: 2026-08-15  
Scope: disposable/local evidence; no parser, spec, README, or public-doc change  
Source checkout: `59dce7b`

## Question

Does the current reader distinguish declared `spec-v0.2`, pre-chain
`spec-v0.1`, missing, future, malformed, and mixed version labels, or does it
only evaluate the existing ledger framing and claim checks?

## Fixture method

Each case used a disposable `.showwork/claims-2026-08-15.jsonl` file with two
claim records and a local `file_exists` check for `marker.txt`. Chained records
used the existing per-file genesis and SHA-256 line links. The fixture was
created and removed under `K:\showwork`; no repository ledger was modified.
The malformed-JSON case added one truncated record after a valid chain.

| fixture | declared label | integrity audit | claim reader | checks observed |
|---|---|---|---|---|
| canonical | `spec-v0.2` | GREEN, 2/2 chained | GREEN | 2/2 passed |
| pre-chain | `spec-v0.1`, no `prev` | YELLOW, 2 pre-chain | GREEN | 2/2 passed; integrity remains unprovable |
| missing version | absent | GREEN, 2/2 chained | GREEN | 2/2 passed |
| future version | `spec-v0.3` | GREEN, 2/2 chained | GREEN | 2/2 passed |
| malformed version | `spec-v0` | GREEN, 2/2 chained | GREEN | 2/2 passed |
| mixed ledger | first record `spec-v0.1`, chained record `spec-v0.2` | GREEN, 1 chained plus 1 pre-chain | GREEN | 2/2 passed |
| malformed JSON after chain | `spec-v0.2` plus truncated line | RED at line 3 | YELLOW | 2/3 parsed/checked; parse error visible |

## Interpretation

The current Python reader and auditor do not negotiate or validate a
`spec_version` field. The version-shaped fields are opaque record data. A
valid chain with a missing, future, or malformed label therefore remains
GREEN, and a pre-chain file remains YELLOW because integrity is unprovable,
not because its version label is rejected. A malformed JSON record is visible
as a reader-side YELLOW parse error and an audit-side RED unchained append after
the chain starts.

The result is not a compatibility claim for another implementation. It shows
only the behavior of the current reader against these local fixtures. No
version-specific refused or unknown state exists in this path; those states
would require an owner-defined version contract and implementation.

## Safe wording

> showwork currently verifies the ledger framing and declared claim checks it
> understands. The tested version-shaped fields are not negotiated by the
> reader. `spec-v0.2` is the repository specification target; labels alone do
> not prove reader compatibility, integrity, adoption, or exact replay.

Do not describe the fixture as a migration, upgrade guarantee, public-doc
contract, or human/AI adoption evidence.

## Verification

- Targeted conformance and audit tests: `python -m pytest tests/test_spec_conformance.py tests/test_audit.py -q` -> `29 passed`.
- Full repository gate already rerun for this repair cycle: `python -m pytest tests/ -q` -> `240 passed`.
- Existing `SPEC.md` remains unchanged at `spec-v0.2`.
