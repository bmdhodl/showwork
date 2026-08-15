# showwork public-proof zero-claim refusal readout r14

Date: 2026-08-15  
Scope: existing local reader commands and synthetic proof roots. No publishing,
traffic measurement, instrumentation, public-copy, verifier, schema, signer,
authority, compliance, adoption, or successful-run claim.

## Reader matrix

| fixture | audit | session verify | evidence pack | safe classification |
|---|---:|---:|---:|---|
| missing `.showwork` ledger | 3 YELLOW, no ledger files | 0 GREEN, `0/0` | 0; pack says YELLOW, 0 sessions, 0 claims | unproven and unavailable |
| empty `.showwork` directory | 3 YELLOW, no ledger files | 0 GREEN, `0/0` | 0; pack says YELLOW, 0 sessions, 0 claims | unproven and unavailable |
| zero-claim closed session | 0 GREEN, 2/2 chained | 0 GREEN, `0/0` | 0; zero claims | vacuous and unproven |
| one valid claim and closed session | 0 GREEN, 3/3 chained | 0 GREEN, `1/1` | 0 | locally backed current claim, with stated limits |

The first three rows are the false-success boundary. The CLI's session verifier
returns `GREEN (0/0)` when there are no claims to evaluate. The evidence pack's
successful process exit does not add claim evidence; its own inventory remains
empty. A closed zero-claim session is not equivalent to a successful run.

## Minimum bundle for a safe answer

The smallest useful bundle is:

1. the raw receipt artifact;
2. a non-empty session verdict with the verified claim count;
3. an audit result for the receipt chain;
4. an explicit session-close event; and
5. a provenance label identifying the local checkout and observation time.

If the non-empty claim evidence is missing, the reader must say **unproven** or
**vacuous**. It must refuse claims of adoption, authority, compliance,
successful execution, exact replay, or outside observation.

## Content recommendation

Keep the refusal visible in human- and AI-facing proof summaries:

> `GREEN (0/0)` means there were no claims to verify. It is not proof of a
> successful run, adoption, authority, compliance, or exact replay.

This is a content-level recommendation only. No public text was changed.

## Decision

**NO CHANGE.** Preserve the current reader contract and use non-empty claim
evidence as the minimum threshold for a positive proof statement.

Validation: `python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r14-full-20260815` -> **234 passed in 11.67s**.
