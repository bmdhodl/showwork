# False Done Rate (FDR)

**How often do AI agents claim work that is not backed by reality?**

Nobody measures this, because measuring it requires receipts: falsifiable
claims recorded at assertion time and verified deterministically against the
filesystem. showwork ledgers make the measurement possible. This document
pre-registers the methodology so the numbers cannot be quietly redefined
after the fact.

## Definitions (normative for any FDR figure we publish)

- **Eligible session** — a session that (a) recorded at least one claim
  carrying a check, and (b) attempted at least one close (a `session.finish`
  or `session.finish.refused` event). Sessions that never claimed anything
  checkable, or never tried to close, are out of population.
- **False-done event** — durable ledger evidence that a "done" was not real
  at the moment it was asserted:
  1. `session.finish.refused` — the exit gate refused a clean close;
  2. an append-only **retraction** record — a claim admitted false;
  3. a close stamped `claims_verdict: RED` — blocked closes and hook-observed
     stops where receipts failed;
  4. a close stamped `verify_bypassed` — a deliberate `--no-verify`. The
     bypass makes the done *unverifiable by choice*; we count it, because an
     unverifiable done and a false done are indistinguishable to a reviewer.
- **FDR (session-level)** — eligible sessions with ≥ 1 false-done event ÷
  eligible sessions.
- **FDR (event-level)** — false-done events ÷ (false-done events + clean
  closes), over eligible sessions.

## Honesty rules

1. **This is a lower bound.** An agent that quietly fixes reality before its
   first `finish` leaves no durable evidence and is invisible to FDR. The
   true rate of "said done before it was done" is ≥ what we publish.
2. **Every number must be reproducible from a published, chain-audited
   ledger.** `showwork audit` GREEN (or the pre-chain portions explicitly
   noted) on the exact corpus, then `python scripts/false_done_rate.py`.
   No screenshots-as-data.
3. **Low rates get published too.** If a corpus shows 0%, that is the
   report. A verification tool that only publishes flattering failure rates
   is lying with its own receipts.
4. **Corpus composition is stated, not implied**: which repos, which agents,
   which date range, what was excluded and why.
5. **No retro-editing.** Corrections to a published figure are appended as
   errata referencing the original, mirroring the ledger's own retraction
   discipline.

## What FDR is not

- Not a model benchmark (yet): our corpora are self-selected production
  repos, small n, one operator. Cross-model comparisons need controlled
  task sets and per-agent session attribution.
- Not a quality score for the *work* — it measures the gap between what an
  agent *said* and what *was*, which is a trust property, not a skill
  property.

## Reproduce

```bash
python scripts/false_done_rate.py --label "name=path" [--label ...] [--json]
```

Day-0 snapshot of our own fleet: [false-done-rate-day0.md](false-done-rate-day0.md).
