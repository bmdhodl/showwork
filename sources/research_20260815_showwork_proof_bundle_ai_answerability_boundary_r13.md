# showwork proof-bundle AI answerability boundary r13

Date: 2026-08-15  
Scope: fixed questions answered from existing local/public README, SPEC,
evidence-pack, PyPI, and GitHub artifacts. No crawler instrumentation, traffic
measurement, adoption, authority, compliance, release, schema, signer, or
public-copy change.

## Answerability matrix

| question | artifact | state | safe answer |
|---|---|---|---|
| What does showwork record? | `SPEC.md`, `README.md` | directly supported | structured claims with session, timestamp, claim, severity, optional artifact/check, and append-only `prev` history |
| What does `verify` prove? | `README.md`, `src/showwork/checks.py` | directly supported | current predicate evaluation against the declared project root and locked command checks |
| What does `audit` prove? | `SPEC.md`, `src/showwork/audit.py` | directly supported | chain integrity, pre-chain status, forks, heads, and exact break location; not claim truth |
| What does the evidence pack prove? | `scripts/evidence_pack.py` | qualified | date-range receipt inventory and chain/current-verification readout; it is not legal advice or a certification |
| What happens to a deleted or cross-paired artifact? | r13 cross-fixture report | directly supported | `verify` is RED while an untouched ledger can remain audit GREEN; the pack marks the failed predicate |
| What happens to a mutated receipt? | r13 cross-fixture report | directly supported | the chain goes RED and the evidence pack refuses |
| Is exact historical replay supported? | r11/r12 context reports, SPEC | refused | no; optional context could support only a qualified rerun |
| Is build provenance or human approval proved? | package crosswalk, official attestation docs | refused | no; machine attestation and local receipt verification are separate evidence classes |
| Is adoption or traffic established? | public GitHub/PyPI pages | refused | no; visible public artifacts are not usage or adoption measurements |

## Content-gap recommendation

A future owner-approved proof bundle could provide a small machine-readable
manifest mapping each public artifact to its command, evidence path, supported
answer, and refusal boundary. That would improve deterministic question
answering without adding crawler instrumentation or changing public copy. This
card does not create that manifest.

Public artifacts inspected: [GitHub repository](https://github.com/bmdhodl/showwork), [PyPI project](https://pypi.org/project/showwork/), and [GitHub offline-attestation guidance](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline).

Decision: **REPAIR-DESIGN-ONLY**; preserve the current narrow proof surface.

