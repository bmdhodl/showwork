# showwork r25 proof-demo time-to-first-receipt readout

Date: 2026-08-15  
Scope: disposable public-package run; report-only  
Card: `proof-demo-time-to-first-receipt-20260815-r25`

## Package boundary

The run installed the published [showwork 0.3.0 package from PyPI](https://pypi.org/project/showwork/)
with `--index-url https://pypi.org/simple` in a fresh virtual environment.
The observed import location was:

`<temp>\showwork-r25-first-receipt-20260815\venv\Lib\site-packages\showwork\__init__.py`

The location was outside the checkout, and the local checkout version `0.3.1`
was not imported. No package was published or changed.

## Reproducible run shape

Disposable project root:

`<temp>\showwork-r25-first-receipt-20260815\project`

It contained only a redacted `receipt.txt`. The first-proof path used five
showwork commands:

1. `showwork start --session first-proof --agent codex`
2. `showwork claim ... --type file_exists --path receipt.txt`
3. `showwork finish --session first-proof --status ok`
4. `showwork verify --session first-proof --no-report`
5. `showwork audit`

The first proof verified `1/1` GREEN. The audit verified `3/3` records
chained. The ledger artifacts were `.showwork/claims-2026-08-15.jsonl` and
`.showwork/sessions.jsonl`.

## Timing and proof matrix

The times below are one Windows/Python 3.13 disposable run. CLI timings are
process wall time and are not an SLA, capacity, reliability, or adoption
measurement.

| phase | elapsed | observed result |
|---|---:|---|
| virtual environment creation | 5,860.6 ms | disposable venv created |
| public package install | 1,550.9 ms | `showwork==0.3.0` installed |
| first CLI process (`start`, cold) | 88.8 ms | session recorded |
| claim process (warm) | 84.2 ms | claim recorded |
| finish process (warm) | 98.1 ms | clean close recorded |
| session verify (warm) | 82.3 ms | GREEN, 1/1 |
| audit (warm) | 86.0 ms | GREEN, 3/3 chained |

The complete run used 12 showwork commands: five happy-path commands, three
false-close commands, three recovery commands, and one final audit.

## Refusal and recovery

The false-close path started a new session, claimed a missing `missing.txt`,
and ran `showwork finish --status ok`. It exited `2`; stdout reported
`claims: RED (0/1 verified)` and stderr reported:

```text
REFUSED: a clean close requires this session's claims to verify. Fix the gap, retract the claim, or finish --status blocked.
```

The recovery path started a separate session, claimed the existing redacted
`receipt.txt`, and finished with exit `0`. The final public-package audit was
GREEN with `9/9` records chained and six session records. This demonstrates
the local refusal/recovery behavior only; it is not a reliability or exact
replay claim.

## Friction and artifact clarity

- The user-visible setup requires a virtual environment plus a public package
  install before the first receipt; install and environment creation dominate
  this run's elapsed time.
- The first trustworthy artifact is the local `.showwork/` ledger, with one
  claims JSONL file and one sessions JSONL file.
- A false close is explicit and machine-readable through exit `2`, with the
  refusal reason on stderr; a corrected separate session can close GREEN.
- The run did not test a human, crawler, traffic source, adoption funnel,
  package release, or local `0.3.1` candidate.

## Owner-gated demo/content decision

Any future demo or public-copy change needs an owner decision on the supported
package version, environment setup, command sequence, output location, and
what “first receipt” means. It should preserve the refusal path and separate
install intent from adoption. This report does not change README/package
content, add tracking, publish, tag, or claim adoption.

## Verification

- Published package identity: `0.3.0`; local checkout excluded: confirmed.
- Happy path, refusal path, recovery path, and final audit: completed.
- Exact disposable project and venv removed: confirmed.
- Full repository gate for this cycle: `python -m pytest tests/ -q` -> 240 passed.
