# showwork package provenance and evidence-pack crosswalk r13

Date: 2026-08-15  
Scope: local candidate package metadata, the current publish workflow, showwork
receipt/evidence fields, and official GitHub/PyPI attestation documentation.
No release, signing, schema, verifier, public-wording, supply-chain,
compliance, authority, or adoption claim.

## Result

Package provenance and showwork receipts answer different questions. A package
attestation can bind a distribution digest to an attesting identity when it is
actually produced and verified. A showwork receipt records a local assertion,
its predicate, current verification result, and ledger chain. Neither artifact
is evidence for the other unless an owner-approved binding is created and
verified.

Official references: [GitHub artifact attestations](https://docs.github.com/en/enterprise-cloud%40latest/actions/concepts/security/artifact-attestations), [GitHub offline verification](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline), [PyPI attestations](https://docs.pypi.org/attestations/), and [PyPI publish attestations](https://docs.pypi.org/attestations/publish/v1/).

## Observed local inputs

- Source commit: `697b8a9ea90e072031538e2db2f4ee3cf7a88b55`.
- Candidate wheel: `showwork-0.3.1-py3-none-any.whl`.
- Candidate wheel SHA-256: `b50f8e0773a707d682a432438d97ff2cada5c3c0e58edd956e233773e46d05df`.
- Local publish workflow includes an OIDC Trusted Publishing path and a token
  fallback; the workflow text is intent/configuration, not a record that this
  candidate was published with an attestation.
- Receipt fields are the SPEC claim identity, timestamp, claim, severity,
  optional artifact, optional check, and `prev` chain link. The evidence pack
  inventories timestamp, session, claim, check, and current verification.

## Field crosswalk

| field/question | package provenance can establish | showwork can establish | safe combined wording | absent/refused wording |
|---|---|---|---|---|
| artifact identity | distribution filename and digest, when attestation subject matches | optional local artifact path/check | “these are separately identified artifacts” | “the receipt proves this wheel’s origin” |
| source revision | attestation predicate may link source/commit | local git state can be claimed separately | “the local run names revision X” | “the uploaded wheel came from X” without binding |
| build identity | attestation can name workflow/identity after verification | no signer or trusted-root check | “the build identity is externally attested” only with verified evidence | “publisher identity is proven by a receipt” |
| receipt chain | not supplied by package attestation | append-only local history and forks | “the local receipt history is chain-auditable” | “the package is chain-bound to this receipt” |
| current-state verification | not supplied by provenance alone | predicate result from current filesystem/command | “the local predicate verified GREEN” | “the package is secure or compliant” |
| timestamp | attestation signing/publish timing when present | receipt assertion time | “these timestamps are recorded separately” | “the events are the same transaction” |
| human authority | not implied by machine identity | absent from current receipt contract | none without owner decision | “a human approved this” |

## Recommendation

Keep the surfaces separate. If a future release wants a crosswalk, make it a
read-only manifest that names package filename/digest, source revision, receipt
head, and current predicate result as separate fields with separate evidence
links. It must explicitly refuse to upgrade local verification into attested
build provenance, security, compliance, or adoption.

Decision: **REPAIR-DESIGN-ONLY**; no documentation or release edit follows.

