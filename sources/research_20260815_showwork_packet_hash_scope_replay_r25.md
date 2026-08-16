# showwork r25 packet-hash scope replay readout

Date: 2026-08-15  
Scope: in-memory redacted packet comparison; report-only  
Card: `packet-hash-scope-replay-matrix-20260815-r25`

## Question and boundary

Which representation changes are distinguished by four candidate comparison
scopes for the same redacted packet? This is a measurement of candidate
normalizations, not a selected showwork identity or replay contract. No
signature, signer, algorithm choice, identity field, verifier, or production
replay behavior was added.

SHA-256 was used only as a fixed comparison instrument and truncated to the
first 16 hexadecimal characters in this report. The experiment does not
recommend SHA-256 or claim a cryptographic guarantee.

## Fixture

The base packet was the following flat redacted object:

```json
{"run":"run-001","claim":"redacted proof is valid","verdict":"GREEN","exit":0,"scope":"local-fixture","revision":"r24","packet_id":"pkt-001","packet_hash":"ab12cd","artifact_path":"proof/receipt.json"}
```

Four candidate scopes were compared:

1. `raw`: serialized bytes as supplied.
2. `normalized`: parsed JSON with sorted keys and compact separators.
3. `decoded`: sorted key/value pairs after JSON decoding.
4. `tuple`: the values of `run`, `claim`, `verdict`, `exit`, `scope`,
   `revision`, and `packet_id`. `packet_hash` and `artifact_path` were
   deliberately excluded to avoid circularity and to expose omission risk.

The selected tuple is an experiment parameter, not a proposed contract.

## Hash-scope matrix

`same` means the candidate digest matched the unmutated base. The digest
prefixes make the comparison reproducible within this fixture.

| mutation | raw | normalized | decoded | selected tuple | candidate disposition |
|---|---:|---:|---:|---:|---|
| canonical | same `2789a27124816007` | same `16ab1c4b4bcac978` | same `54fc7e4a9f92c937` | same `9185850b67c0ff0f` | answer baseline |
| key order reversed | different | same | same | same | raw refuse; other scopes qualify as representation candidates |
| CRLF pretty-print | different | same | same | same | raw refuse; other scopes qualify as representation candidates |
| outer whitespace | different | same | same | same | raw refuse; other scopes qualify as representation candidates |
| path `proof/...` -> `./proof/...` | different | different | different | same | raw/normalized/decoded refuse; tuple unknown because path is omitted |
| claim text changed | different | different | different | different | refuse under every scope |
| revision `r24` -> `r25` | different | different | different | different | refuse under every scope |
| verdict `GREEN` -> `RED` | different | different | different | different | refuse under every scope |
| exit `0` -> string `"0"` | different | different | different | different | refuse under every scope |
| packet ID case changed | different | different | different | different | refuse under every scope |
| packet hash hex case changed | different | different | different | same | raw/normalized/decoded refuse; tuple unknown because hash is omitted |

The dispositions are a conservative hypothetical comparison vocabulary for
this readout only:

- `answer` is the unchanged baseline.
- `qualify` is a representation-equivalence candidate that still needs an
  owner decision and a decisive-field check.
- `unknown` is an omitted-field or unresolved-scope case.
- `refuse` is a mismatch under the named scope.

None of these labels is emitted by showwork, and none proves replay or
provenance.

## Collisions and false-match examples

- Normalized, decoded, and selected-tuple scopes collide on key order, line
  endings, and outer whitespace. These are intentional representation
  collisions in the fixture, not cryptographic collisions.
- The selected tuple collides on path spelling because `artifact_path` is not
  selected. If path identity mattered, that would be a false-match candidate.
- The selected tuple also collides on packet-hash case because `packet_hash`
  is excluded. It cannot decide whether hash text is case-sensitive.
- No pair in the fixture produced equal raw-byte digests after a semantic
  mutation. That observation is local to these inputs and does not establish
  collision resistance.

## Owner-gated identity contract

Before any implementation, the owner must choose the covered bytes/fields,
normalization rules, treatment of paths and line endings, revision and
verdict semantics, packet-hash circularity handling, and the refusal behavior
for omitted or contradictory values. The decision must include fixtures for
benign formatting, changed proof, stale revision, and malformed input.

No replay guarantee, provenance guarantee, signature, or public identity
contract is claimed by this report.

## Verification

- In-memory redacted fixture: completed; no repository or public files changed.
- Candidate scopes and all mutation rows recorded above.
- Full repository gate for this cycle: `python -m pytest tests/ -q` -> 240 passed.
