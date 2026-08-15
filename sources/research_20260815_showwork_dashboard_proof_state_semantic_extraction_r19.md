# showwork dashboard proof-state semantic extraction readout r19

Date: 2026-08-15  
Status: observed / disposable parser only  
Scope: six synthetic inputs rendered by the current static dashboard and
inspected with a stdlib `HTMLParser`; no dashboard/UI, markup, tracking,
schema, or accessibility-conformance change.

## Result

Every state produced the same semantic shell: one h1, one h2, seven table
headers, zero links, no table caption, and zero `th[scope]` attributes. The
fixed warning was present for every state. Verdict, revision, observed date,
fork heads, exit-gate state, and receipt links were not serialized from the
fixture fields.

| state | headings | table headers | links/caption | proof markers extracted |
|---|---|---:|---|---|
| valid | `showwork — agent control`, `Interventions` | 7 | 0 / none | no GREEN, revision, receipt, or exit-gate marker |
| zero-claim | same | 7 | 0 / none | no empty-corpus qualification or proof verdict |
| RED/refused | same | 7 | 0 / none | no RED or REFUSED marker |
| stale | same | 7 | 0 / none | no observed date or source revision |
| forked | same | 7 | 0 / none | no fork count, heads, or provenance |
| blocked | same | 7 | 0 / none | no blocked status or owner-action field |

The dashboard's fixed interpretation text did extract consistently:
`Read this correctly.`, `would have fired here`, `this saved money`, `market
evidence`, and `No spend column`. A state word can appear incidentally in the
Signal column when supplied as a fixture reason, but that is not a semantic
verdict field and does not distinguish current truth from replay context.

## Human versus AI ambiguity

Humans can recognize this as an intervention/replay report. A deterministic AI
reader cannot safely answer whether a row is GREEN, RED, stale, forked, or
blocked, nor follow a receipt/report link because none is present. The absence
of a link is also not proof that the underlying receipt is absent.

## owner-gated recommendation

Define a read-only extraction contract before any UI work: identity, as-of
time, source revision, claim count, audit/session verdict, exit-gate state,
fork heads, provenance, and explicit links. Keep replay/refusal boundaries
visible and do not infer authority, compliance, adoption, or current truth.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r19-full-20260815` -> **239 passed**.
