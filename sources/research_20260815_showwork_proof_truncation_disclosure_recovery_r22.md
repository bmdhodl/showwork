# showwork r22: proof-truncation disclosure and recovery

Date: 2026-08-15  
Scope: disposable redacted packets and deterministic human/AI-shaped reader
fixtures. No packer, serializer, schema, dashboard, or public-copy change.

## Recovery matrix

| fixture | identity/full packet | human-shaped reader | AI-shaped reader | safe decision |
|---|---|---|---|---|
| full available | same run and packet identity | recovered with matched full packet | recovered with matched full packet | answer |
| missing full packet | no complete packet | refuse | refuse | refuse |
| mismatched full packet | run and packet identity differ | refuse identity mismatch | refuse identity mismatch | refuse |
| restored full packet | same identity after availability | recovered with matched full packet | recovered with matched full packet | answer |
| contradictory status/exit | status ok with command exit 2 | refuse contradiction | refuse contradiction | refuse |

The readers preserved the disclosed truncation boundary. A complete packet was
usable only when it was available and bound to the same run and packet
identity. A mismatched or missing packet did not recover the original claim.
The contradictory fixture refused even though its claims verdict was GREEN.

## Boundary and recommendation

Matching a full packet supports a bounded recovery statement for this fixture;
it is not a recovery guarantee, signature, provenance proof, or exact-replay
claim. Any future two-tier reader contract is owner-gated and must keep
identity mismatch, missing evidence, and contradictory fields fail-closed.

Validation: python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r22-full-20260815 -> **240 passed**
