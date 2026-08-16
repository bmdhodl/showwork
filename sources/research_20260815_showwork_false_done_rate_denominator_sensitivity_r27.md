# False-done rate denominator sensitivity — r27

Date: 2026-08-15  
Scope: report-only, disposable local ledgers; no FDR methodology, day-0 data,
README, case study, public metrics, or script changes.  
Source card: `false-done-rate-denominator-sensitivity-readout-20260815-r27.md`

## Question

How do eligibility, false-done event classes, repeated events, and labeled
corpora change the session-level and event-level FDR outputs? The existing
definitions in `docs/false-done-rate.md` and implementation in
`scripts/false_done_rate.py` were treated as read-only contracts.

## Disposable fixture

The fixture used two temporary roots and was removed after measurement.
`cases` contained:

| session shape | included in eligible denominator? | false evidence |
|---|---:|---|
| clean close with a checked claim | yes | none |
| refused close, then corrected clean close | yes | one refused close |
| retraction, then clean close | yes | one retraction |
| RED close | yes | one RED close |
| `no_verify` close | yes | one bypass |
| two retractions plus RED close | yes | three events |
| prose-only claim | no | not eligible |
| checked claim with no close | no | not eligible |

`clean-control` contained two clean closes and one RED close. The fixture used
the existing ledger writer for claims, retractions, and normal/refused closes;
the RED close was a disposable ledger event matching the existing event shape.
No repository ledger was modified.

## Input-to-metric matrix

| labeled corpus | eligible sessions | false-done sessions | false-done events | clean closes | checked claims | session FDR | event FDR |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cases` | 6 | 5 | 7 | 3 | 7 | 83.3% | 70.0% |
| `clean-control` | 3 | 1 | 1 | 2 | 3 | 33.3% | 33.3% |
| aggregate, additive across labeled roots | 9 | 6 | 8 | 5 | 10 | 66.7% | 61.5% |

The aggregate session denominator is the sum of eligible sessions across
labels. The aggregate event denominator is false-done events plus clean
closes. A repeated event increases event FDR but cannot increase the number
of false-done sessions beyond one for that session. The `retract-1` session
also demonstrates that a retraction remains a false-done event even when a
later clean close exists.

Command used:

```text
python scripts/false_done_rate.py --json --label "cases=<temporary-root>" --label "clean-control=<temporary-root>"
```

Focused behavioral coverage remained green:

```text
python -m pytest tests/test_false_done_rate.py -q
5 passed in 0.10s
```

## Reader-safe interpretation

These outputs are denominator demonstrations, not a production FDR figure.
Any human- or AI-facing answer must name the exact corpus, date/range,
eligibility rule, event rule, excluded sessions, and whether values are
session- or event-level. A session rate and an event rate are not interchangeable.
The result remains a durable-evidence lower bound: a quiet correction before
the first close is invisible. A small or synthetic corpus cannot support an
adoption, quality, prevalence, or cross-agent claim.

## Evidence and external-standard gaps

Evidence is synthetic and local only. No external standard, independent
reviewer, production corpus, or public artifact was used, so this readout does
not establish external validity, inter-rater agreement, or reproducibility by
another operator. The existing methodology's requirement for an exact,
chain-audited corpus remains unsatisfied by this disposable fixture. No
methodology change is proposed from that gap.

## Boundary

This readout does not edit `scripts/false_done_rate.py`,
`docs/false-done-rate.md`, day-0 data, README, case-study metrics, schemas,
adapters, signing/timestamps, public copy, releases, or real Git state.
