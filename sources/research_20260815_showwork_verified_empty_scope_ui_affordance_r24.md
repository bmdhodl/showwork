# showwork verified-empty scope and UI affordance inventory r24

Date: 2026-08-15  
Source revision: 6f55b4a  
Scope: read-only inspection of README, CLI output, and the existing static
dashboard renderer plus disposable local CLI fixtures. No UI, accessibility,
workflow, tracking, or public-copy change.

## Surface inventory

| surface | visible evidence | scope/action affordance | accessible name or role |
|---|---|---|---|
| public README | `showwork verify`, GREEN/RED, `REFUSED`, exit 2, and `budget_exceeded` wording | no verified-empty scope or state-to-action matrix | prose/code blocks; no rendered role applicable |
| local CLI | GREEN session output, RED false claim, `REFUSED` guidance, and `session.finish recorded` for blocked close | no declared scope; refusal gives corrective next actions; blocked close has no reason in the one-line output | terminal text; no HTML name/role |
| static dashboard renderer | intervention table, `reason` tag, session/project/call data, and native headings/table | no proof state, declared scope, empty-state action, or refusal affordance | native `h1`, `h2`, `table`, `th`, and `td`; no explicit `aria-*` or `role=` observed |

## State inventory

| state | visible status | declared scope | allowed next action | refusal meaning | safe classification |
|---|---|---|---|---|---|
| `verified_empty` | not a first-class CLI/dashboard label | missing | missing | not represented | unknown; cannot infer global emptiness |
| `no_evidence` | not a first-class CLI/dashboard label | missing | missing | not represented | unknown; not success |
| `RED` | CLI verification reports `0/1 verified` | missing | CLI says fix the gap or retract | explicit through `REFUSED` on clean close | refuse |
| `refused` | CLI prints `REFUSED` and exit 2 on a false clean close | missing | fix, retract, or close blocked | explicit in CLI text | refuse |
| `blocked` | CLI records `session.finish` with `status=blocked` | missing | owner review or later correction is not rendered by current surface | not a clean success; no public reason label | qualify/unknown |
| `timeout_unknown_descendant` | README mentions `budget_exceeded`; no descendant-unknown label | missing | cleanup/review/rerun contract is missing | not represented | unknown; do not infer termination |

The disposable local fixture produced GREEN for a valid claim, `REFUSED` and
exit 2 for a false clean close, and a blocked close event. Rendering a
synthetic intervention produced HTML with the reason and native table
semantics, but no proof-state, scope, `aria-*`, or explicit `role=` affordance.
This is an inventory, not a human study or accessibility conformance claim.

## Boundary

The missing state-to-scope/action affordances are evidence for an owner-gated
future UI/content decision only. No UI or accessibility implementation was
made, and no human-comprehension or adoption conclusion follows.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
