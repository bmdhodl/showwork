# Case study: the receipts from a real agent operation

## Why this exists

An agent reported three completed actions. Two had not happened. The run looked
successful in chat and its tool trace looked busy, but the asserted outcomes
were false.

The response was not another prompt asking agents to be careful. The operation
added a falsifiable claims grammar, deterministic checkers, an append-only
ledger, and an exit gate that refuses a clean finish when a RED claim fails.
showwork is the extracted version of that system.

## Sanitized production evidence

The public aggregate was derived from the private production ledger. No claim
text, internal path, strategy, financial value, or trading record was copied.

| Receipt | Measured value |
|---|---:|
| Claims recorded | 2,158 |
| Claims with deterministic checks | 2,152 |
| Agent sessions represented | 842 |
| Append-only retraction records | 152 |
| Dated claim ledgers | 19 |
| State-audit reports | 43 |
| False completion claims in the origin incident | 2 |
| Malformed ledger lines surfaced | 1 |
| Latest captured audit | RED, 54/60 verified |

The RED result is part of the evidence. The system does not turn stale, broken,
or malformed proof into a green marketing metric. It exposes the gap.

Retractions are corrections, not a claim that all 152 original assertions were
malicious or false. They preserve the original record and the later correction
without rewriting history.

## Reproduce the aggregate

Run the derivation against a vault checkout:

```bash
python scripts/derive_case_study.py \
  --vault /path/to/vault \
  --output docs/case-study-metrics.json
```

The generated [`case-study-metrics.json`](case-study-metrics.json) includes a
SHA-256 fingerprint of the exact source ledgers used. Re-running against the
same inputs produces the same aggregate and fingerprint.

## The operating pattern

1. Start an agent session.
2. Record every material completion claim with a deterministic check.
3. Verify the claim against the real artifact or command result.
4. Refuse a clean finish when a RED claim fails.
5. Append a retraction when an earlier assertion was wrong.
6. Keep the entire history.

That pattern matters more than the Python package. A different implementation
can follow [`spec-v0.1`](../SPEC.md) and produce the same kind of evidence.
