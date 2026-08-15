# showwork packet identity canonicalization matrix r24

Date: 2026-08-15  
Source revision: 6f55b4a  
Scope: ten redacted representation mutations over the r23 identity tuple.
No canonicalization code, serializer, identity field, signing scheme, or
replay guarantee was added.

## Matrix

The candidate binding tuple is `run`, `claim`, `verdict`, `exit`, `scope`,
`revision`, `packet_id`, and `packet_hash`.

| representation | mutation | classification | hash-scope assumption |
|---|---|---|---|
| JSON key order | reordered keys | qualify | semantic hash required; raw-byte hash changes |
| line endings | LF versus CRLF | qualify | safe only if text normalization is explicit |
| outer whitespace | trimmed scalar | unknown | no trim rule is assumed |
| path spelling | slash, case, or root variant | unknown | path identity is unresolved |
| revision notation | `abc` versus `refs/heads/main@abc` | refuse | revision identity differs |
| claim whitespace | internal claim text changed | refuse | claim bytes or meaning differ |
| verdict case | `green` versus `GREEN` | qualify | enum case-folding must be explicit |
| exit type | `0` versus string `"0"` | qualify | type coercion must be explicit |
| packet-id case | `packet-a` versus `PACKET-A` | refuse | identity token differs |
| hash hex case | lowercase versus uppercase hex | qualify | same decoded bytes only if hex parsing is explicit |

`answer` is reserved for an exact representation under a declared hash scope.
`qualify` means a future contract could normalize the representation, but the
current fixture cannot assume it. `unknown` means identity is unresolved;
`refuse` means the representation changes a decisive identity value.

## Boundary

Hash scope must be decided before any attachment or replay contract. This
matrix does not select a canonicalization algorithm and is not a provenance or
replay guarantee. Any future identity contract remains owner-gated and must
state whether it hashes raw bytes, normalized fields, or decoded values.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
