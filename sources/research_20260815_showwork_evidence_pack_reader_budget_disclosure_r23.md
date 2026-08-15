# showwork evidence-pack reader budget disclosure r23

Date: 2026-08-15  
Source revision: 128eea9  
Scope: six redacted local pack shapes, three disclosure variants, and three
reader shapes. This is not a production threshold, SLA, serializer, packer,
dashboard, or public-copy change.

## Fixture and disclosure variants

Pack shapes: `full`, `field_separated`, `bounded_with_marker`,
`bounded_without_marker`, `malformed`, and `contradictory`.

Disclosure variants:

1. `none`;
2. `short_warning`: “This result may be incomplete.”;
3. `explicit_full_packet`: “Truncated or bounded result: exact claims require
   the full packet; malformed or contradictory packets are unverified.”

Readers: plain-text, structural, and AI-shaped. The matrix contains 54
pack-disclosure-reader cells.

## Disclosure matrix summary

| pack shape | no disclosure | short warning | explicit full-packet disclosure | safe result |
|---|---|---|---|---|
| full | exact claim safe | exact claim safe | exact claim safe | complete packet |
| field-separated | exact claim safe | exact claim safe | exact claim safe | complete fields |
| bounded with marker | not exact-safe; full packet needed | not exact-safe; full packet needed | qualified; full packet needed | claim loss is disclosed only by the explicit contract |
| bounded without marker | not exact-safe; false-complete risk | not exact-safe; false-complete risk | qualified; full packet needed | absence of a marker never proves completeness |
| malformed | refuse | refuse | refuse | parse failure is not proof |
| contradictory | refuse | refuse | refuse | status and exit disagreement is not proof |

The same safe result was applied to all three reader shapes. The explicit
disclosure is the only tested variant that names both exact-claim loss and the
need for a full packet. It qualifies a bounded result; it does not turn a
bounded projection into a complete proof. Malformed and contradictory packs
remain refusal states regardless of disclosure text.

## Interpretation boundary

This fixture measures a redacted reader contract, not latency, capacity,
performance, an SLA, or human comprehension. It does not justify changing a
pack format or size limit. Any future content-contract decision remains
owner-gated and must retain the refusal behavior for malformed and
contradictory evidence.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
