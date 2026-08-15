# showwork r22: dashboard reason-label cross-reader fixture

Date: 2026-08-15  
Scope: disposable HTML fixtures and text/DOM-role/AI-shaped deterministic
readers. No dashboard, UI, tracking, accessibility, or public-copy change.

## Cross-reader matrix

| fixture variant | plain text | DOM-role reader | AI-shaped reader | ambiguity |
|---|---|---|---|---|
| no label | ambiguous | ambiguous | ambiguous | false-success and false-refusal risk |
| one label | exact state | exact state with role=status | exact state | verified-empty still needs action boundary |
| one reason code | ambiguous | reason-only | reason-known | state/action ambiguity remains |
| label plus reason | exact state | exact state plus reason | exact state plus reason | lowest ambiguity in fixture |

The matrix covered no evidence, verified empty, RED, refused, and blocked. A
plain-language label was enough for all three readers to identify the tested
state. A reason code alone was not enough for the plain-text reader and did
not supply a human action explanation even when a structured reader recognized
the code. The no-label control remained ambiguous.

The verified-empty label was identified correctly but must not be interpreted
as populated successful work. Every reader still needs an explicit action
boundary for that state. The role=status observation is structural fixture
evidence, not an accessibility-conformance claim.

An owner-gated minimal content contract may choose a label/reason pair after
review. No dashboard implementation, UI, tracking, public-copy, accessibility,
schema, adoption, or compliance change is supported.

Validation: python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r22-full-20260815 -> **240 passed**
