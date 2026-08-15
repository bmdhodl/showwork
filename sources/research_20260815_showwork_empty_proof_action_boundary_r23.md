# showwork empty-proof action boundary r23

Date: 2026-08-15  
Source revision: 128eea9  
Scope: six redacted local fixtures x three reader shapes. No dashboard, UI,
tracking, accessibility, workflow, or public-copy change.

## Fixture matrix

The disposable fixture set contained 6 states and 3 reader shapes, for 18
state-reader cells: `verified_empty`, `no_evidence`, `RED`, `refused`,
`blocked`, and `timeout_unknown_descendant`; readers were plain-text,
structural, and AI-shaped.

| state | safe interpretation | allowed next action | forbidden inference |
|---|---|---|---|
| `verified_empty` | complete for the declared scope | stop and record the empty result | the whole system is empty |
| `no_evidence` | unknown / unproven | collect or inspect evidence | success |
| `RED` | failed or contradictory | inspect, fix, or retract the claim | the run passed |
| `refused` | exit gate refused completion | correct the claim or close blocked | override the refusal |
| `blocked` | incomplete and needing owner review | resolve the blocker or request owner review | completion |
| `timeout_unknown_descendant` | budget exceeded; descendant state unknown | review cleanup and rerun when safe | exact termination or completion |

Each reader shape received the same state, action, and forbidden-inference
contract. The fixture therefore tests wording consistency, not visual
rendering or human comprehension.

## False-reading boundary

An empty verified result is bounded by its declared scope. It is not a global
absence claim. `no_evidence`, `RED`, `refused`, and `blocked` are not success
states. A timeout with unknown descendant state must remain unresolved; it
cannot be converted into a clean termination claim by a reader.

The content-contract recommendation is owner-gated. It must preserve these
state distinctions if considered later; this readout does not propose or
implement a vocabulary or dashboard change.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
