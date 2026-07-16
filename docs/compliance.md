# Compliance evidence packs

Audit-trail requirements don't ask "what did the agent do?" — they ask
**"prove the record is faithful."** That is precisely what an integrity-
chained receipts ledger can do, and `scripts/evidence_pack.py` turns a date
range of it into an auditor-readable bundle: control ↔ receipt ↔ chain proof.

> **Not legal advice.** The pack is supporting evidence prepared by the
> operator. It is not a certification and does not by itself establish
> compliance with any framework. Sufficiency is a determination for your
> auditor or counsel — bring them the pack, not this README.

## Generate

```bash
python scripts/evidence_pack.py --from 2026-07-01 --to 2026-07-31 \
    --framework all --out evidence-july.md
# redact client identifiers or private paths from rendered text:
python scripts/evidence_pack.py --from ... --to ... \
    --redact 'client-\w+' --redact 'C:/Users/[^ ]+' --out ...
```

A sample generated from this repository's own ledger:
[evidence-pack-sample.md](evidence-pack-sample.md).

## What's inside

1. **Integrity section** — chain-audit verdict and per-file head hashes at
   export time. Anyone holding the ledger can re-derive the heads; one
   altered byte anywhere in chained history changes them. The generator
   **refuses to produce a pack from a RED (tampered) ledger** — evidence
   that cannot prove it was not edited is not evidence.
2. **Activity summary** — sessions, claims, verification-at-export counts,
   exit-gate refusals, bypass stamps.
3. **Control mapping** — what the ledger demonstrates against:
   - **EU AI Act** Art. 12 (record-keeping) and Art. 26(6) (deployer log
     retention) — enforcement wave from 2026-08-02;
   - **SOC 2** CC8.1 (change management), CC7.2/7.3 (monitoring, event
     evaluation);
   - **HIPAA Security Rule** 164.312(b) (audit controls), 164.316(b)
     (documentation retention).
4. **Receipt inventory** — every claim in range with its check type and
   whether it verifies at export time.

## Reading "verifies at export time" honestly

A claim records what was true **when it was asserted**. Reality moves: a
claim that pinned "35 tests passed" fails re-verification after the suite
grows to 75. That is not tampering (the chain proves the record itself is
untouched) — it is the difference between *point-in-time truth* (stamped on
the session's close verdict) and *current truth* (recomputed at export).
Auditors get both, labeled.

## Redaction

`--redact REGEX` masks matches in rendered session ids and claim text.
Redaction changes the *pack*, never the ledger — the underlying records stay
intact and re-auditable by parties cleared to see them. List your client
names, internal hostnames, and private paths before sharing a pack
externally.
