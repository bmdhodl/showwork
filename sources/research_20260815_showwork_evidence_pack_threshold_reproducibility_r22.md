# showwork r22: evidence-pack threshold reproducibility

Date: 2026-08-15  
Scope: 20 disposable ledger shapes (1, 4, 16, and 32 claims crossed with
64, 512, 1024, 2048, and 4096-character fields), each repeated with seeds 11,
23, and 47. No pack format, limit, serializer, storage, or SLA change.

## Repeatability result

All 20 shapes and all three seeds per shape had pack exit 0, GREEN chain
audits, expected parse counts for full/field-separated/bounded projections,
and exact decisive claims in the full and field-separated projections. Pack
byte sizes were identical across the three seeds for every shape in this
deterministic fixture.

At 64-character fields, the synthetic 256-character bound retained the exact
claim and did not mark truncation. At 512, 1024, 2048, and 4096-character
fields, every claim-count shape lost exact bounded claim text while exposing a
truncation marker. This repeats the reader hazard across counts, but it is a
behavior of the disposable bound, not a production threshold or capacity
claim.

A malformed control audited RED, pack generation exited 2, and REFUSED was
visible. A contradictory control with status ok, GREEN claims, and command
exit 2 was classified refuse.

## Boundary and recommendation

An owner-gated representation decision may use this repeatability result to
design a broader corpus, but must not call it an SLA, throughput limit,
performance guarantee, or production crossover. No packer, serializer, schema,
dashboard, storage, or adoption change was made.

Validation: python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r22-full-20260815 -> **240 passed**
