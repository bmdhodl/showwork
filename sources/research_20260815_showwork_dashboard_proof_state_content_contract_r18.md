# showwork dashboard proof-state content contract readout r18

Date: 2026-08-15  
Status: observed / owner-gated recommendation  
Scope: disposable inputs passed to `src/showwork/dashboard.py::render`; no
HTML, CSS, tracking, public schema, or accessibility claim was added.

## Result

The current static dashboard is a replay/intervention readout, not a complete
proof-state reader. Every fixture renders the same identity, five aggregate
stats, an interventions table, a fixed interpretation warning, and threshold
metadata. Fixture fields such as revision, verdict, exit-gate state, observed
date, fork count, and branch heads are ignored unless a fixture deliberately
places a state word in the visible `reason` or project text. That makes the
current output insufficient to distinguish observed proof from stale,
refused, blocked, or forked state.

## Current visible contract

| surface | current visible content |
|---|---|
| document identity | title `showwork - agent control`; h1 `showwork — agent control`; static/offline subtitle |
| aggregate stats | runs observed, tool calls, interventions, stuck rate, calls after trip |
| table | Signal, Session, Project, Repeated call, Fired at, Length, Ran on |
| empty case | one `No interventions.` row and zero-valued aggregate stats |
| interpretation boundary | retroactive replay, “would have fired here,” not “this saved money,” owned-fleet dogfooding, and no spend column |
| footer | thresholds, generator script names, self-contained/offline statement |

The implementation exposes one `main`-like content wrapper but no semantic
navigation landmark. The table has headers but no caption, scoped headers, or
proof-state links. Those are observations for a future owner decision, not an
accessibility conformance verdict.

## Disposable state matrix

| fixture state | visible result now | omitted or ambiguous proof field |
|---|---|---|
| valid / observed | replay row and detector metrics; a supplied reason can appear as Signal | no explicit GREEN, source revision, claim count, session close, or observed timestamp |
| zero-claim | zero stats and `No interventions.` | cannot distinguish a healthy empty corpus from missing, filtered, or unprocessed data |
| RED / refused | a supplied refusal-like reason can appear as Signal | no verdict, failed claim count, `REFUSED` close state, or refusal explanation |
| stale | only ordinary replay fields; a reason word is not a freshness contract | no source revision, as-of date, freshness state, or stale boundary |
| forked | ordinary replay fields; a reason word may be shown | no fork count, branch heads, chain verdict, or provenance link |
| blocked | ordinary replay fields; a reason word may be shown | no blocked status, exit-gate outcome, pending owner action, or current-truth disclaimer |

The fixtures included extra fields for `source_revision`, `verdict`,
`exit_gate`, `observed_at`, `forks`, `heads`, and `status`; the renderer did
not serialize those fields. This is a content-contract observation, not a
request to change the renderer in this batch.

## Human and AI reader boundaries

The fixed warning correctly prevents several overreads: replay is not live
intervention, “would have fired” is not savings, and owned-fleet data is not
market evidence. It does not identify which displayed row is current, stale,
RED, blocked, or forked. A human can read the table as an intervention report;
an AI extracting status from it cannot safely infer a proof verdict, authority,
compliance, adoption, or current truth.

## Owner-gated recommendation

Before any UI change, define a read-only content contract with explicit labels
for identity, observed/as-of time, source revision, claim count, audit verdict,
session exit-gate status, fork count and heads, provenance, and links back to
the receipt/report. Keep the existing replay warning and add explicit
“observed replay” language to any future state label. Do not publish a schema
or imply adoption, authority, compliance, or current truth from this static
artifact.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r18-full-20260815` -> **239 passed**.
