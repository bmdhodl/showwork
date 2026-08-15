# showwork dashboard proof-reader/accessibility readout r17

Date: 2026-08-15  
Scope: five disposable `showwork.dashboard.render` fixtures inspected through a
local loopback browser page and accessibility snapshots. No dashboard HTML/CSS,
tracking, public traffic, accessibility conformance, adoption, compliance, or
authority claim.

## Fixture matrix

| fixture | visible result | safe reader interpretation | gap |
|---|---|---|---|
| valid intervention | one run, five calls, one intervention, one table row | replayed intervention observation | no receipt verdict, claim count, source revision, or provenance field |
| zero claims | all five stats are zero; table says `No interventions.` | empty replay input | does not explicitly say zero claims are vacuous/unproven |
| RED/refused-shaped row | arbitrary signal text can say `claims RED / close refused` | a replay row with that label | dashboard has no structured RED/session-close field; text alone is not a receipt verdict |
| stale source context | fixture metadata held `source_revision: unavailable` and `verdict: GREEN` | visible page shows only one run and one call | source age/revision and verdict are omitted from rendering |
| fork-shaped input | two rows display two interventions | two replay rows were rendered | fork count, branch heads, and authority/refusal boundary are omitted |

## Browser/accessibility observations

The browser page title was `showwork - agent control`; the accessibility snapshot
exposed one `h1`, one `h2`, a real `table`, seven column headers, the warning
text, and a `footer`. At a 360px viewport the cards stacked and the document
itself did not overflow, while the table remained a 640px horizontal region
inside `.scroll`.

The static page currently has zero `main` or `nav` landmarks, zero interactive
elements, no table `caption`, zero `th[scope]` attributes, and the `.scroll`
region has `overflow-x: auto` but no `tabindex`, role, or accessible label. The
snapshot therefore makes the text readable, but a keyboard or assistive reader
has no explicit entry point for the horizontal table and no semantic source for
the proof distinctions the fixtures carried.

## Bounded recommendation

**REPAIR-DESIGN-ONLY:** a future dashboard revision should expose artifact
identity, observation date/source revision, claim count, verdict, and refusal
boundary as structured visible fields; add a `main` landmark and labeled,
keyboard-reachable table overflow; and give headers/caption explicit semantics.
This fixture audit does not justify changing the dashboard or claiming user
accessibility/traffic.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
