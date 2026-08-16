# Detached-head and timestamp-anchor boundary — r27

Date: 2026-08-15  
Scope: report-only, disposable local ledgers and synthetic anchor receipts; no
signing, timestamping, credentials, release metadata, public claims, or real
Git state changes.  
Source card: `detached-head-timestamp-anchor-boundary-readout-20260815-r27.md`

## Local contract

`showwork audit` proves the local append-only relationship: each `prev` points
to an earlier line or the genesis anchor. It exposes the compatibility
`head`, every branch `heads`, fork count, and a verdict. A fork is GREEN when
its anchors resolve, but it gives up linearity and requires each branch head to
be treated separately. A missing or mismatched external receipt does not turn
the local audit RED; it only removes the external claim.

## Synthetic matrix

The fixture created a two-record linear ledger and a three-record forked
ledger in temporary directories. It then compared synthetic receipts by head
hash and required-field presence. The values below are deliberately not
cryptographic signatures or timestamps.

| case | local verdict | local heads | local forks | external interpretation | safe refusal wording |
|---|---|---:|---:|---|---|
| valid linear receipt | GREEN | 1 | 0 | receipt covers the current compatibility head and has all synthetic fields | “local chain and supplied receipt agree for this head; no publisher or time authority is established” |
| mismatched linear receipt | GREEN | 1 | 0 | receipt digest/head mismatch | “refuse the anchored claim; local integrity remains a separate GREEN result” |
| missing linear receipt | GREEN | 1 | 0 | no external anchor supplied | “local head is available; external anchoring is unavailable” |
| stale linear receipt | GREEN | 1 | 0 | receipt covers a prior head after a new append | “receipt is stale for the current head; do not use it as current evidence” |
| partial linear receipt | GREEN | 1 | 0 | head matches but timestamp/proof fields are incomplete | “receipt is incomplete; do not infer signed time or inclusion” |
| fork receipt covers one branch | GREEN | 2 | 1 | one published branch head is covered; the other is not | “receipt is branch-scoped; it does not anchor every current head” |

The synthetic linear audit contained two chained records and one head. The
synthetic fork contained three chained records, one fork, and two heads. The
fixture was deleted after the run.

## External comparison and gap

The [Sigstore Bundle Format](https://docs.sigstore.dev/about/bundle/) describes
a bundle as verification material plus signature content, with transparency
log entries and timestamps supplying evidence used during verification. That
is a comparison vocabulary only. This report creates no Sigstore bundle,
signature, RFC3161 timestamp, transparency-log entry, inclusion proof, key
binding, identity assertion, or verifier.

Therefore a synthetic receipt field named `signedEntryTimestamp` or
`inclusionProof` is not evidence that those semantics are valid. External
standard conformance, publisher identity, authority, clock provenance,
inclusion, and revocation behavior remain untested gaps. No adoption,
compliance, supply-chain, or release claim follows.

## Boundary

No source file, SPEC text, schema, adapter, signing path, timestamp path,
credential, public copy, release artifact, or real Git checkout changed.
