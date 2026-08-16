# showwork r25 proof-state accessible-status fixture

Date: 2026-08-15  
Scope: disposable DOM/CLI projection and current-renderer inventory  
Card: `proof-state-accessible-status-fixture-20260815-r25`

## Reference boundary

The [WAI-ARIA 1.2 Recommendation](https://www.w3.org/TR/wai-aria-1.2/)
describes roles, states, properties, and accessibility-tree semantics. W3C's
[WCAG 2.2 status-message guidance](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
describes status messages that can be programmatically determined through a
role or property and presented without taking focus. These are reference
standards for the fixture, not evidence that showwork conforms to either
standard.

## Disposable projection

Each state was projected as a small HTML fragment with:

```html
<section aria-label="Proof state">
  <h2>STATE LABEL</h2>
  <p>Scope: declared local scope</p>
  <p role="status" aria-live="polite" aria-atomic="true">Status: STATE LABEL</p>
  <p>Next action: one allowed local action</p>
  <p>Boundary: not a certification, adoption, accessibility-conformance, or exact-replay claim.</p>
</section>
```

A stdlib `html.parser` structural reader collected visible text and a
synthetic accessibility-tree reader checked the named region, status role,
polite live-region setting, atomicity, and status text. This is not a browser,
screen reader, accessibility API, or human study.

## State-to-affordance matrix

All six synthetic rows passed the fixture checks: visible label, declared
scope, exactly one allowed next action, explicit forbidden inference, named
region, status role/live settings, and status text.

| state | visible label | declared scope | one allowed next action | forbidden inference | fixture status semantics |
|---|---|---|---|---|---|
| verified-empty | `VERIFIED: empty scope` | local disposable fixture only | inspect local receipt | certification/adoption/replay excluded | role=status, polite, atomic |
| no-evidence | `NO EVIDENCE` | no qualifying local receipt | add one falsifiable claim | same boundary | role=status, polite, atomic |
| RED | `RED: proof failed` | local fixture claim failed | inspect failed check | same boundary | role=status, polite, atomic |
| refused | `REFUSED: clean close blocked` | local unverified claim | fix or retract claim | same boundary | role=status, polite, atomic |
| blocked | `BLOCKED: operator action required` | local session blocking note | review blocking note | same boundary | role=status, polite, atomic |
| timeout-unknown | `UNKNOWN: timeout scope unresolved` | descendant termination not established locally | keep unresolved | same boundary | role=status, polite, atomic |

The projection intentionally gives each state one next action without turning
that action into an authority, compliance, adoption, or exact-replay claim.

## Current renderer inventory

The existing `showwork.dashboard.render` was also called with an empty local
results set. It produced 3,899 UTF-8 bytes with one native `h1`, one native
`h2`, no explicit `aria-*` attribute, and no explicit `role=` attribute. This
reconfirms the r24 inventory: the current dashboard has native document
semantics and intervention copy, but it does not expose the six proof states,
scope, or a programmatic status announcement as a first-class contract.

The inventory is descriptive only. No dashboard, CLI, ARIA, workflow, tracking,
public-copy, accessibility, or human-comprehension change was made.

## Findings and owner gate

The fixture demonstrates a possible reader contract, not implementation or
conformance. The current product surface leaves proof-state labels and next
actions outside a durable UI contract. An owner would need to decide the state
vocabulary, scope wording, forbidden inferences, native HTML versus ARIA
semantics, live-region timing, localization, keyboard behavior, and browser/
assistive-technology test plan before any change.

No accessibility conformance, human comprehension, agent comprehension,
adoption, or traffic claim follows from this deterministic fixture.

## Verification

- Six state projections: all structural and synthetic-tree fixture checks passed.
- Current dashboard inventory: 3,899 bytes; `aria-*` absent; explicit `role=` absent.
- Full repository gate for this cycle: `python -m pytest tests/ -q` -> 240 passed.
