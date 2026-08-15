# showwork legacy chain-history classification

Date: 2026-08-15
Scope: read-only audit classification. No migration, re-chain, deletion,
verifier/schema, signing, public-copy, legal, or release change.

## Result

KEEP the existing audit surface. The whole-corpus `YELLOW` is explained by
historical pre-chain records, while the chained records have no current break.
Accepted concurrent forks are reported separately from tampering. Rewriting
the old records would destroy the evidence needed to explain the boundary.

## Exact observations

```text
python -m showwork.cli audit --json
exit 3, verdict YELLOW, total_records 394, total_chained 362, total_forks 43
```

Pre-chain records total 32:

| Ledger file | Records | Chained | Pre-chain | Classification |
|---|---:|---:|---:|---|
| `claims-2026-07-09.jsonl` | 2 | 0 | 2 | Legacy pre-chain |
| `claims-2026-07-10.jsonl` | 13 | 0 | 13 | Legacy pre-chain |
| `claims-2026-07-11.jsonl` | 1 | 0 | 1 | Legacy pre-chain |
| `claims-2026-07-16.jsonl` | 45 | 42 | 3 | Boundary file with anchored legacy records |
| `sessions.jsonl` | 152 | 139 | 13 | Legacy lifecycle records plus current chain |

Fork observations are also explicit:

- `claims-2026-07-17.jsonl` has 19 accepted forks.
- `claims-2026-08-15.jsonl` has 1 fork across 2 heads.
- `sessions.jsonl` has 23 accepted forks across 35 heads.
- No file reported `break_at`; ordinary audit therefore found no tampered
  chained byte.
- `python -m showwork.cli audit --strict` exits 2 and reports RED because
  strict mode forbids forks. That is a policy result, not a new tamper finding.

The prior disposable tamper fixture remains the contrasting case: audit
exited 2 RED and `evidence_pack.py` exited 2 without writing a pack. The
current checkout does not show that RED chain condition.

## Classification contract

| State | Reader label | Current verifier behavior |
|---|---|---|
| Pre-chain | `LEGACY / integrity not provable under current chain` | File is YELLOW and records are retained |
| Chained | `CHAINED` | Hash links and heads are checked |
| Forked | `CHAINED WITH ACCEPTED FORK` | Ordinary audit stays GREEN and exposes heads; strict mode is RED |
| Tampered | `RED CHAIN` | Exact break is RED; evidence pack refuses |
| Empty or unavailable | `UNVERIFIED` | No historical event is established |

## Decision

NO CHANGE. Keep history immutable, keep ordinary and strict fork policy
separate, and use the existing per-file details when an operator needs the
legacy/current distinction.
