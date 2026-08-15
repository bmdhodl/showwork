# showwork r21: evidence-pack field-budget crossover

Date: 2026-08-15  
Scope: disposable local ledgers and synthetic full, field-separated, and
bounded reader projections. No pack format, serializer, limit, hosted
behavior, or SLA change.

## Step matrix

| step | claims x length | pack bytes | full projection | field-separated | bounded | pack/audit | exact claim: full / field / bounded |
|---|---:|---:|---:|---:|---:|---|---|
| small | 4 x 64 | 2665 | 960 | 656 | 1040 | exit 0 / GREEN | yes / yes / yes |
| count | 16 x 64 | 4171 | 3840 | 2624 | 4160 | exit 0 / GREEN | yes / yes / yes |
| length | 4 x 2048 | 10601 | 8896 | 8592 | 1808 | exit 0 / GREEN | yes / yes / no |
| crossover | 16 x 2048 | 35915 | 35584 | 34368 | 7232 | exit 0 / GREEN | yes / yes / no |

All three projections parsed back to the expected claim count at every valid
step. At 64-character claims, the 256-character synthetic bound did not
truncate. At 2048-character claims, the bounded projection became much
smaller but lost the exact decisive claim, while full and field-separated
representations retained it. This is a representation crossover in the
fixture, not a production capacity boundary.

A malformed control audited RED, caused pack generation to exit 2, and exposed
REFUSED. The failure remained visible rather than becoming a usable evidence
pack.

## Boundary and recommendation

An owner-gated representation review may profile a larger corpus and choose
whether a bounded reader is acceptable for a specific use. Any chosen bound
must make truncation and proof loss explicit. No packer, serializer, schema,
dashboard, performance, SLA, hosted-service, or adoption claim is supported.

Validation: python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r21-full-20260815 -> **239 passed**
