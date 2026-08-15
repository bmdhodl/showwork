# showwork attestation-shaped mismatch policy fixture r13

Date: 2026-08-15  
Scope: ephemeral non-cryptographic metadata beside a synthetic local artifact,
then existing showwork `verify` and `audit` commands. No signature
verification, trusted root, hardware attestation, receipt format, schema,
signer, authority, compliance, adoption, exact-replay, or public-release claim.

## Result

The fixture policy can classify metadata as observed, unproven, or refused, but
showwork does not consume the metadata or cryptographically verify it. All four
cases kept showwork `verify` and `audit` at exit 0 because the local receipt only
checked artifact presence. That separation is the result, not a missing hidden
feature.

Official context: [GitHub says attestations must be verified and are not a guarantee that an artifact is secure](https://docs.github.com/en/enterprise-cloud%40latest/actions/concepts/security/artifact-attestations); [PyPI describes attestations as signatures binding a release distribution to a digest and identity](https://docs.pypi.org/attestations/).

## Fixture matrix

The metadata named `artifact.txt`, a SHA-256 digest, publisher, build identity,
and timestamp. The synthetic policy used 2026-08-15 13:00 UTC as its reference
time and a 24-hour freshness window.

| input | digest | identity | timestamp | policy classification | showwork verify/audit |
|---|---|---|---|---|---|
| matching digest | match | present | fresh | `observed-but-unproven` | 0 / 0 |
| mismatched digest | mismatch | present | fresh | `refused` | 0 / 0 |
| missing publisher/build identity | match | missing | fresh | `unproven` | 0 / 0 |
| stale timestamp | match | present | stale | `refused` | 0 / 0 |

The matching case observes local byte equality and metadata presence only. It
does not prove a signature, trusted root, publisher, build, or artifact origin.
The mismatch and stale cases refuse policy use. Missing identity remains
unproven even though the local digest matches.

## Cleanup and boundary

All metadata and artifact fixtures were created under one temporary directory;
the harness verified that the directory was removed after the context exited.
No fixture was copied into `.showwork/` or committed. The current verifier
remains the authority for current local predicates only.

Decision: **KEEP** the report-only policy boundary. No signing or verifier work
follows.

