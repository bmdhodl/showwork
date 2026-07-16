# False Done Rate — Day-0 report (2026-07-16)

First measurement of the [False Done Rate](false-done-rate.md) on our own
agent fleet's production ledgers. Frozen machine-readable snapshot:
[false-done-rate-day0.json](false-done-rate-day0.json).

## Corpus

Three production repos operated by one person's autonomous agent fleet
(Claude Code, Codex, and scheduled nightly workers), all running the showwork
prompt contract + Stop-hook since 2026-07-11; plus this repository, which has
dogfooded its own ledger since genesis (2026-07-09). One fleet repo (an OSS
SDK) is excluded: its local checkout sits on a pre-adoption branch, so its
ledger was not readable at measurement time. Exclusions stated per the
methodology's honesty rules.

## Results

| corpus | eligible sessions | false-done sessions | FDR (session) | FDR (event) | checked claims |
|---|---:|---:|---:|---:|---:|
| showwork (this repo) | 8 | 3 | 37.5% | 47.1% | 32 |
| fleet web repo | 8 | 5 | 62.5% | 44.0% | 36 |
| fleet trading repo | 5 | 1 | 20.0% | 20.0% | 18 |
| **all** | **21** | **9** | **42.9%** | **40.4%** | 86 |

**In the first week of receipts, 9 of 21 agent sessions (42.9%) produced at
least one "done" that was not backed by reality when asserted — and every
one of them was caught by a deterministic gate before it shipped.**

## What the false dones actually were

- `v02-phase-1` (this repo): while building the tamper-evident ledger
  itself, the developing agent recorded a claim whose regex had been mangled
  by shell quoting. The exit gate REFUSED the close — twice (the first
  correction was also wrong). Two append-only retractions later, the session
  closed GREEN. The gate caught its own author, mid-feature.
- Fleet web repo (5 sessions): nightly content/design agents claiming file
  changes and funnel fixes that had not landed as described — refused at
  close, fixed or retracted, then closed clean.
- Fleet trading repo (1 session): a market-watch session whose claimed
  artifact did not match reality at close. (Session bookkeeping only —
  verification is never in the order path.)

## Caveats, stated up front

- **n = 21 sessions.** This is a day-0 snapshot, not a study. It becomes a
  study as the corpus accumulates nightly.
- **Lower bound by construction**: agents that fix reality before their
  first `finish` leave no durable evidence.
- **Self-selected corpus**: one operator's repos, agents already running
  under a verification contract. Agents with no gate plausibly assert false
  dones *more* often, not less — but that is a hypothesis, not a finding.
- **No cross-model comparison** is supported by this data.

## Reproduce

```bash
python scripts/false_done_rate.py --label "name=path" ...
showwork audit   # chain-verify the corpus before quoting it
```
