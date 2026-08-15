# showwork fork-density performance readout r12

Date: 2026-08-15  
Scope: synthetic local claim ledgers at 100 and 500 records with controlled
fork, retraction, pre-chain, clean, and tampered variants. No capacity,
reliability, customer-scale, authority, compliance, adoption, signer, or
public-release claim.

## Result

Ordinary audit accepts valid forks as GREEN and reports them. Strict audit
refuses the same forked structures as RED. Evidence-pack generation succeeds
for ordinary valid fixtures and exits 2 for tampered fixtures. Retraction
records remain visible in the ledger and are excluded from the active-claim
verification denominator. These are bounded synthetic observations, not
capacity or adoption evidence.

Decision: **KEEP** the current fork/refusal semantics. No production change is
warranted by this readout.

## Harness

The local harness generated deterministic JSONL records with a shared anchor,
controlled branch records, optional pre-chain records, and optional retraction
records. Each active claim checked one local marker file. For each fixture it
measured `audit_root`, `audit_root(strict=True)`, `verify_date`, and the
evidence-pack builder with `time.perf_counter()` and `tracemalloc`.

## Raw timing matrix

Times are milliseconds from one Windows 11 / Python 3.13.2 run. `pack` is the
rendered output size for ordinary fixtures; tampered rows show refusal text
size, not an evidence pack.

| n | forks | retract | pre-chain | tamper | audit | strict | verify | pack exit | pack ms | pack bytes | peak KiB |
|---:|---:|---:|---:|:---:|---:|---|---:|---:|---:|---:|---:|
| 100 | 0 | 0 | 0 | no | 10.949 | GREEN | 27.698 | 0 | 28.435 | 12,803 | 276.2 |
| 100 | 0 | 10 | 0 | no | 8.340 | GREEN | 24.084 | 0 | 26.493 | 11,900 | 263.9 |
| 100 | 10 | 0 | 0 | no | 6.594 | RED | 26.905 | 0 | 28.889 | 12,803 | 270.0 |
| 100 | 10 | 10 | 0 | no | 7.943 | RED | 25.090 | 0 | 27.741 | 11,891 | 261.9 |
| 100 | 25 | 0 | 0 | no | 9.366 | RED | 26.320 | 0 | 28.899 | 12,803 | 276.0 |
| 100 | 25 | 10 | 0 | no | 7.134 | RED | 23.336 | 0 | 26.777 | 11,891 | 265.4 |
| 100 | 10 | 10 | 10 | no | 8.319 | RED | 23.274 | 0 | 27.237 | 11,890 | 262.0 |
| 100 | 10 | 10 | 0 | yes | 5.323 | RED | 25.185 | 2 | 0.874 | 648 | 193.9 |
| 500 | 0 | 0 | 0 | no | 16.218 | GREEN | 130.573 | 0 | 140.765 | 49,603 | 1,233.0 |
| 500 | 0 | 50 | 0 | no | 16.319 | GREEN | 120.047 | 0 | 128.844 | 45,062 | 1,208.8 |
| 500 | 50 | 0 | 0 | no | 15.422 | RED | 131.712 | 0 | 141.781 | 49,603 | 1,243.9 |
| 500 | 50 | 50 | 0 | no | 16.019 | RED | 121.252 | 0 | 130.725 | 45,051 | 1,222.7 |
| 500 | 125 | 0 | 0 | no | 16.803 | RED | 131.492 | 0 | 142.594 | 49,603 | 1,263.6 |
| 500 | 125 | 50 | 0 | no | 16.411 | RED | 124.223 | 0 | 135.487 | 45,003 | 1,240.4 |
| 500 | 50 | 50 | 10 | no | 16.078 | RED | 123.287 | 0 | 134.909 | 45,042 | 1,221.4 |
| 500 | 50 | 50 | 0 | yes | 9.204 | RED | 118.337 | 2 | 1.861 | 648 | 948.8 |

For clean non-tampered rows, ordinary audit remained GREEN even with forks;
strict audit became RED as soon as a fork was present. For tampered rows, the
ordinary audit and strict audit were RED and the evidence pack refused with
exit 2. The audit stops at the first anchored break, so its `records` count in
those refusal cases is only the inspected prefix. The claim verifier can still
report GREEN when the tampered bytes do not affect the claim predicates; chain
integrity and predicate truth are separate checks.

## Boundary

Fork counts and timing from this fixture do not identify an authoritative head,
prove human resolution, or establish a service capacity limit. No capacity or adoption claim
follows from this synthetic fixture. Keep the current read-only
observability and refusal paths.
