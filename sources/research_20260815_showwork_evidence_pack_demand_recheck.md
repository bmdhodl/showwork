# Research sources: evidence-pack demand recheck

Date: 2026-08-15
Date window: 2026-07-16 through 2026-08-15

## First-party surface status

- `https://bmdpat.com/evidence-pack` returned HTTP `404` on 2026-08-15.
- `https://bmdpat.com/api/subscribe` returned HTTP `405` to a read-only GET.
  No POST or test signup was sent, so this check created no funnel event.
- The implementation branch for the proposed waitlist page is
  `feat/evidence-pack-waitlist`; PR #1081 is `CLOSED`, `mergedAt: null`, with
  failed hosted/PC checks recorded in the live PR metadata.
- The completed Vault artifact is internal and escalated; it contains no
  first-party submission rows. A direct subscriber-table query was not
  available in this read-only pass.

## Classification

- External human: 0 observed rows. This means no attributable row was
  available, not that the private database has been proven empty.
- Owner: PR #1081 and the internal queue artifact; neither is demand.
- Synthetic/test: 0 created. No signup was submitted.
- Crawler/mirror/unknown: GitHub and PyPI traffic only; attribution is not
  available from the counts.

## Current distribution comparison

- GitHub `bmdhodl/showwork`: 0 stars, 1 fork, 2 open issues, 0 subscribers;
  traffic endpoint 116 clones and 81 unique cloners.
- PyPI `showwork`: public version `0.3.0`, uploaded 2026-07-18; recent
  downloads 2 day, 14 week, 336 month.

These are distribution signals, not evidence-pack demand or showwork adoption.

## Decision

HOLD the demand test. Continue only after a live page exists and a read-only
first-party event query can attribute at least one external human signup or
direct inbound to the evidence-pack surface. If the surface remains absent and
no attributable event is available at the next review on 2026-09-15, KILL the
test rather than building the pack or inferring demand from downloads, forks,
or owner activity.
