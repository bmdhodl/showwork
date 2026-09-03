# showwork JSON canonicalization chain boundary r14

Date: 2026-08-15  
Scope: temporary synthetic receipts and the existing `audit`, `verify`, and
`evidence_pack.py` commands. No serialization, hash, chain, schema, verifier,
signer, authority, compliance, adoption, exact-replay, or public-release
change.

## Result

The current ledger is sensitive to JSON token bytes after the line has been
written, except for line-ending changes that `line_hash` intentionally strips.
RFC 8785/JCS defines a separate canonical representation with no whitespace,
recursive property sorting, and preserved array order. That comparison is
useful for design language only. It does not authorize showwork to adopt JCS or
to reinterpret existing receipts.

## Synthetic matrix

Each case began with one valid claim, a closed session, and an unchanged
`artifact.txt`. Exit codes are the existing CLI exits: audit/pack `0` is
GREEN, `2` is RED, and verify `0`/`2` is current-state pass/fail.

| mutation | audit | session verify | evidence pack | interpretation |
|---|---:|---:|---:|---|
| original JSON | 0 GREEN, 3/3 chained | 0 GREEN, 1/1 | 0 | valid local observation |
| top-level and recursive property reorder | 2 RED, break at `sessions.jsonl` line 2 | 0 GREEN, 1/1 | 2 refused | receipt bytes changed; current claim still happens to pass |
| whitespace inserted between JSON tokens | 2 RED, break at `sessions.jsonl` line 2 | 0 GREEN, 1/1 | 2 refused | formatting is part of the chained line identity |
| check pattern changed from `v1` to `v2` in the claims tip | 0 GREEN, 3/3 chained | 2 RED, 0/1 | 0, pack contains `XX` | chain can remain intact while the current predicate fails |

The semantic tip mutation is intentionally recorded as a boundary: the last
line has no later pointer to expose its rewrite, but `verify` catches the
changed predicate and the generated pack records the failed result. A saved
external head or pack comparison would be a separate owner decision.

## Research comparison

[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html) describes a hashable
JSON representation using deterministic property sorting, recursive sorting of
objects inside arrays, and no emitted whitespace. It also treats canonicalized
JSON as a possible wire format, which is different from showwork's current
append-only raw-line contract.

The experiment therefore separates three questions:

1. Is the JSON semantically parseable? The existing readers can still parse the
   reordered and whitespace-mutated lines.
2. Does the raw receipt chain remain anchored? Rewriting an interior line makes
   `audit` RED because the next `prev` no longer matches.
3. Does the recorded predicate still pass? A semantic check-value mutation can
   make `verify` RED even when the chain is GREEN.

## Decision

**NO CHANGE.** Keep the current byte-sensitive chain semantics and document JCS
only as an external comparison. Do not canonicalize historical receipts,
claim cross-language interoperability, or add a signing/verifier surface from
this readout.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r14-full-20260815` -> **234 passed in 11.67s**.
