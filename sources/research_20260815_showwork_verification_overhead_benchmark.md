# showwork verification-overhead benchmark

Date: 2026-08-15  
Scope: disposable synthetic local corpora only. No customer data, hosted
service, schema change, receipt-format change, public claim, adoption claim,
or release claim.

## Result

The benchmark exposed a clear safe optimization: before the change,
`record_claim` rescanned the entire ledger before every append. On a 1,000
claim synthetic corpus that took 9,351 ms. A process-local last-record hash
cache with file-size/mtime invalidation and a full-scan fallback reduced the
same append to 1,054 ms. Audit and refusal behavior stayed intact.

The largest post-change wall cost was 1,054 ms for appending 1,000 claims. The
largest traced Python allocation peak was 2,604 KiB for 1,000-claim session
verification. These are local measurements, not a capacity guarantee.

## Environment and generator

- OS: Windows 11, build `10.0.26200`.
- Python: `3.13.2` (`C:\Python313\python.exe`).
- Local showwork source: `0.3.1`, working-tree base commit
  `3b114185e4aab56c196971936174cfcd051d4ad0`.
- Corpus: a temporary root with one non-secret `artifact.txt` and claims
  using `{"type":"file_exists","path":"artifact.txt"}`.
- Sizes: 10, 100, 500, and 1,000 claims.
- Measurements: `time.perf_counter()` wall time and Python
  `tracemalloc` peak per operation.
- Variants at 500 claims: intact green, tampered chain red, one retraction,
  and two-branch fork.

The exact temporary generator was
`<temp>\showwork-verification-overhead-20260815.py`.
Its reproducible recipe is:

```python
for size in (10, 100, 500, 1000):
    root = disposable_root()
    write(root / "artifact.txt", "synthetic benchmark artifact")
    for index in range(size):
        record_claim(root, session, f"synthetic claim {index}",
                     check={"type": "file_exists", "path": "artifact.txt"})
    measure(verify_session, verify_date, audit_root, build_pack)

red = copy(green_500); alter_one_claim_byte(red)
retracted = copy(green_500); record_retraction(retracted, first_claim)
forked = copy_prefix(green_500, split=250)
append_two_branches_from_the_common_parent(forked, 125, 125)
```

Each operation wrote its JSON result with wall milliseconds, traced peak KiB,
verdict/counts, and evidence-pack exit/byte/write status. The benchmark ran
before and after the cache change; the post-change raw output is preserved
below.

## Before/after green corpus timings

| Operation | Before cache | After cache | Result |
|---|---:|---:|---|
| Append 10 | 68.778 ms | 10.892 ms | 10 claims written |
| Append 100 | 722.966 ms | 102.494 ms | 100 claims written |
| Append 500 | 3,927.302 ms | 522.161 ms | 500 claims written |
| Append 1,000 | 9,351.444 ms | 1,054.113 ms | 1,000 claims written |
| Verify session, 1,000 | 480.552 ms | 288.699 ms | `GREEN`, 1,000/1,000 |
| Verify date, 1,000 | 344.511 ms | 280.935 ms | `GREEN`, 1,000/1,000 |
| Audit, 1,000 | 28.333 ms | 26.275 ms | `GREEN` |
| Evidence pack, 1,000 | 365.857 ms | 299.423 ms | exit 0, 92,217 bytes |

The append improvement is approximately 89% at 1,000 claims. Verification,
audit, and pack timings are within the same bounded local-run order; the
optimization does not change the ledger format or verifier.

## State and refusal matrix

| Variant | Verify-date result | Audit result | Evidence-pack result |
|---|---|---|---|
| Green 500 | `GREEN`, 500/500 | `GREEN` | exit 0, written |
| Tampered chain 500 | Claim checks remain `GREEN`, 500/500 | `RED` | exit 2, not written |
| Retracted 500 | `GREEN`, 499/499 active | `GREEN` | exit 0, written; retraction retained |
| Forked 500 | `GREEN`, 500/500 | `GREEN`, one observed fork/two heads | exit 0, written |

The red-chain distinction is intentional: claim verification and chain audit
answer different questions. A pack refuses on a RED chain even when individual
predicates still pass. A fork remains observable and accepted under ordinary
fork-tolerant audit; it is not authority or adoption evidence.

## Raw post-change output

```text
green-10-append-10-claims 10.892 ms; peak 14.3 KiB
green-10-verify-session GREEN 10/10; 7.998 ms
green-10-verify-date GREEN 10/10; 3.526 ms
green-10-audit GREEN; 5.828 ms
green-10-evidence-pack exit 0, 3173 bytes, written; 5.311 ms
green-100-append-100-claims 102.494 ms; peak 18.9 KiB
green-100-verify-session GREEN 100/100; 34.106 ms
green-100-verify-date GREEN 100/100; 26.924 ms
green-100-audit GREEN; 6.811 ms
green-100-evidence-pack exit 0, 11110 bytes, written; 31.089 ms
green-500-append-500-claims 522.161 ms; peak 24.8 KiB
green-500-verify-session GREEN 500/500; 145.378 ms
green-500-verify-date GREEN 500/500; 137.010 ms
green-500-audit GREEN; 16.156 ms
green-500-evidence-pack exit 0, 46710 bytes, written; 144.529 ms
green-1000-append-1000-claims 1054.113 ms; peak 26.2 KiB
green-1000-verify-session GREEN 1000/1000; 288.699 ms; peak 2604.3 KiB
green-1000-verify-date GREEN 1000/1000; 280.935 ms
green-1000-audit GREEN; 26.275 ms
green-1000-evidence-pack exit 0, 92217 bytes, written; 299.423 ms
red-chain-500-verify-date GREEN 500/500; 153.273 ms
red-chain-500-audit RED; 2.586 ms
red-chain-500-evidence-pack exit 2, 1052 bytes, not written; 1.897 ms
retracted-500-verify-date GREEN 499/499; 150.547 ms
retracted-500-audit GREEN; 10.992 ms
retracted-500-evidence-pack exit 0, 46710 bytes, written; 149.540 ms
forked-500-verify-date GREEN 500/500; 153.963 ms
forked-500-audit GREEN; 11.165 ms
forked-500-evidence-pack exit 0, 49240 bytes, written; 158.426 ms
```

## Implementation and tests

`src/showwork/ledger.py:38,233-256` now caches the last hash only when file
size and `st_mtime_ns` still match. A changed file falls back to the existing
full `_record_lines` scan. `tests/test_audit.py:36-59` covers cache reuse and
external-append invalidation. Focused audit tests passed `24`; the full suite
must remain the release gate.

## Decision

KEEP the cache optimization as a local implementation improvement. It changes
no JSON fields, hash rules, verifier semantics, fork policy, evidence-pack
refusal, public copy, or release surface. Do not treat these synthetic timings
as hosted-scale, customer, compliance, or adoption evidence.
