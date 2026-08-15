# showwork truncation full-packet binding and staleness r23

Date: 2026-08-15  
Source revision: 128eea9  
Scope: redacted local receipt/packet tuples only. No signing, identity-schema,
serializer, packer, replay, or provenance guarantee was added.

## Binding fixture

The bounded receipt carried a reference tuple of `run`, `claim`, `verdict`,
`exit`, `scope`, `revision`, `packet_id`, and `packet_hash`. A complete packet
was considered current only when all tuple fields matched. Human and
AI-shaped readers received the same matrix.

| packet case | mismatched fields | human classification | AI-shaped classification |
|---|---|---|---|
| same-run current | none | answer | answer |
| same-run current with bounded disclosure | none; bounded receipt still requires the full packet | qualify | qualify |
| same-run stale | revision, packet_hash | refuse | refuse |
| regenerated with new identity | packet_id, packet_hash | unknown | unknown |
| cross-run | run, claim, packet_id, packet_hash | refuse | refuse |
| identity mismatch | packet_id | refuse | refuse |

## Safe interpretation

Only an exact current tuple can answer the proof question. A bounded receipt
may be qualified by a matching full packet, but the bounded projection alone
does not recover omitted claims. A stale packet is not current merely because
its run label matches. A regenerated packet with a new identity remains
unknown until an explicit binding contract exists; it is not silently accepted.
Cross-run and identity-mismatched packets refuse for both reader shapes.

This is a local policy fixture, not a replay or provenance guarantee. Any
future complete-packet attachment contract remains owner-gated and must be
specified before implementation.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
