# showwork r20: dashboard empty-state reader boundary

Date: 2026-08-15  
Scope: disposable local HTML fixtures and the existing reader output only. No dashboard source, UI copy, tracking, or accessibility claim changed.

## Probe

Six redacted states were rendered: `no-data`, `zero-claims`, `valid-empty-scope`, `RED`, `refused`, and `blocked`. The probe recorded stat-node count, intervention count, verdict markers, links, warning text, and HTML size.

| fixture | zero stat nodes | no interventions | green | red | refused | blocked | links | warning | bytes |
|---|---:|---|---|---|---|---|---:|---|---:|
| no-data | 4 | true | false | false | false | false | 0 | true | 3899 |
| zero-claims | 4 | true | false | false | false | false | 0 | true | 3899 |
| valid-empty-scope | 4 | true | false | false | false | false | 0 | true | 3920 |
| RED | 4 | true | false | false | false | false | 0 | true | 3899 |
| refused | 4 | true | false | false | false | false | 0 | true | 3899 |
| blocked | 4 | true | false | false | false | false | 0 | true | 3899 |

The only consistent reader cue was the generic `Read this correctly.` warning. It did not identify absent data, a healthy empty scope, failed proof, a refused close, or a blocked run. The small byte difference for `valid-empty-scope` came from the synthetic threshold payload, not a semantic state marker.

## Boundary and recommendation

The current output is not answerable as a proof-state reader for empty or failed inputs. A reader can safely say only that no populated interventions were rendered. It cannot infer GREEN, RED, refusal, blocked execution, or a valid empty scope from this output.

An **owner-gated** content-contract review may define explicit state labels and a zero-claim rule. This is a recommendation only. No dashboard implementation, schema, tracking, accessibility, adoption, or compliance change belongs to this readout.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r20-full-20260815` -> **239 passed**
