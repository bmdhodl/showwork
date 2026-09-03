# showwork proof-pack hash versus chain integrity readout r14

Date: 2026-08-15  
Scope: synthetic local evidence packs, artifact bytes, receipt lines, chain
heads, and the existing `audit`, `verify`, and `evidence_pack.py` commands. No
signing, attestation, second verifier, schema, supply-chain, authority,
compliance, adoption, exact-replay, or public-release change.

## Result

An artifact digest, a receipt chain head, a claim result, and a rendered pack
hash answer different questions. A matching hash is an identity comparison,
not authorization, provenance, security, or compliance evidence.

## Field and mutation matrix

| mutation | audit | verify | pack | what changed / what remained out of scope |
|---|---:|---:|---:|---|
| unchanged artifact, ledger, and pack | 0 GREEN, 3/3 | 0 GREEN, 1/1 | 0 | baseline local observation |
| `artifact.txt` changed from `v1` to `v2` | 0 GREEN, 3/3 | 2 RED, 0/1 | 0 with `XX` claim row | chain stayed intact; current-state predicate failed |
| receipt claim text changed at the ledger tip | 0 GREEN, 3/3 | 0 GREEN, 1/1 | 0 | chain head changed, but no later pointer detected the isolated tip rewrite |
| historical ledger line changed | 2 RED | 0 GREEN, 1/1 | 2 refused | current predicate can still pass, but chain integrity refuses the pack |
| rendered `pack.md` bytes changed by an operator note | 0 GREEN, 3/3 | 0 GREEN, 1/1 | not rechecked by existing CLI | SHA-256 changed from `49fb11e3f608786aae9c169291e5b110a17517a061e5fccbeb9fc883a83e4395` to `e48e2a96e72995e7edd1e3e95a5dfb094aba6f66656bd4f8ca6afcecf8e01ab9`; the pack is outside the ledger chain |

The historical-line row is the same bounded tamper shape exercised by the
companion exit-taxonomy fixture. The tip-line row is deliberately different:
the current chain proves continuity from the preceding record, not an
out-of-band comparison with a previously published head.

## Reader language

Safe:

> The receipt chain is intact, and the declared predicate passed against the
> current local artifact at check time.

Also safe:

> The pack bytes match the separately recorded digest.

Refused:

> The matching hash authorizes the artifact, proves secure supply-chain
> provenance, proves authorship, or establishes compliance.

[GitHub's artifact-attestation guidance](https://docs.github.com/en/enterprise-cloud@latest/actions/concepts/security/artifact-attestations)
distinguishes signed provenance from verification and warns that an
attestation is not a guarantee that an artifact is secure. This report uses
that as a comparison boundary only; it does not add attestation support.

## Decision

**NO PRODUCT CHANGE.** Keep the existing independent checks. If a future owner
chooses to distribute a pack digest or a chain head, it must be labeled as an
external comparison anchor and must not be described as authorization,
security, compliance, or adoption proof.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r14-full-20260815` -> **234 passed in 11.67s**.
