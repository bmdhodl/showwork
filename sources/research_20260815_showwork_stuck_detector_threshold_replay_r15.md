# showwork stuck-detector threshold replay readout r15

Date: 2026-08-15  
Scope: bounded synthetic `ToolCall` sequences through the existing detector.
No real prompts or fleet transcript was used. No threshold default, guard,
verifier, schema, signer, authority, compliance, adoption, public-copy, or
release change.

## Thresholds and sequence matrix

The documented defaults are repeat `3` within a window of `12`, alternation
`3`, and `no_progress` disabled (`None`).

| sequence | configuration | result | detection point | evidence |
|---|---|---|---:|---:|
| identical `Read(same.txt)` x3 | repeat 3 | stuck / `repeat` | call 3 | 3 fingerprints |
| `A-B` x3 | alternation 3 | stuck / `alternation` | call 6 | 2 tool fingerprints |
| nine distinct reads | repeat 3 | not stuck | — | — |
| `Edit(mutated)` + `Test` repeated for 3 cycles | repeat 3 | not stuck | — | mutations reset the window |
| six distinct reads | no-progress 6 enabled | stuck / `no_progress` | call 6 | 6 fingerprints |
| same six reads with default no-progress disabled | defaults | not stuck | — | — |

Synthetic replay completed in under 0.1 ms per sequence. The calibration gap is
intentional: these sequences show detector mechanics, not production false
positive rates, agent intent, or fleet reliability. The existing live guide's
historical replay evidence remains separate from this fixture.

## Decision

**KEEP DEFAULTS.** Preserve repeat and alternation behavior and keep
`no_progress` disabled by default. A future threshold change requires workload
measurement against real, attributable transcripts; this readout does not
enable it or publish a detection rate.

Canonical local evidence: `src/showwork/guards.py`,
`docs/live-enforcement.md`, and `tests/test_guards.py`.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r15-full-20260815` -> **234 passed in 13.27s**.
