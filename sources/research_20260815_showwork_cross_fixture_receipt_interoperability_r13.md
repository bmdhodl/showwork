# showwork cross-fixture receipt interoperability r13

Date: 2026-08-15  
Scope: temporary synthetic roots using only the existing `start`, `claim`,
`verify`, `audit`, and `evidence_pack.py` commands. No second verifier, signer,
schema, portable protocol, authority, compliance, adoption, exact-replay, or
public-release claim.

## Result

The existing path binds a receipt to the current local artifact through its
claim predicate, but it does not make the evidence pack refuse a valid chain
whose artifact predicate is currently RED. A mutated receipt breaks the chain
and the pack refuses. A deleted or cross-paired artifact leaves the chain
GREEN, makes `verify` RED, and produces a pack with a failed-claim marker.

Decision: **KEEP** the current behavior and document the distinction between
chain integrity and claim truth. No interoperability feature is warranted.

## Commands and matrix

Each valid fixture had two claims: an exact marker-content check and a file
existence check. Fixture A and fixture B used separate temporary roots and
sessions. The pack was generated for `2026-08-15` with all existing framework
sections.

| case | verify | audit | pack exit | pack result | cleanup |
|---|---:|---:|---:|---|---|
| valid receipt/artifact A | 0 GREEN | 0 GREEN | 0 | no failed claim | temporary roots removed |
| mutated receipt check | 2 RED | 2 RED | 2 | refused on chain RED | temporary roots removed |
| deleted artifact | 2 RED | 0 GREEN | 0 | `XX` failed claim | temporary roots removed |
| receipt A with artifact B | 2 RED | 0 GREEN | 0 | `XX` failed claim | temporary roots removed |
| valid receipt/artifact B | 0 GREEN | 0 GREEN | 0 | no failed claim | temporary roots removed |

The cross-paired case changes only the artifact bytes while retaining receipt A
and its session. The existing verifier correctly evaluates the predicate
against the current root; it does not infer an external fixture identity.

## Boundary

`audit` proves the ledger chain, not that an artifact still satisfies the
claim. `verify` evaluates the claim against current state, not historical
state. `evidence_pack.py` refuses a RED chain but can render a chain-valid pack
containing a current failed predicate. This is not external interoperability
or exact replay.

