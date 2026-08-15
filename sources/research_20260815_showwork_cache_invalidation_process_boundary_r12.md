# showwork cache invalidation process boundary r12

Date: 2026-08-15  
Scope: synthetic local ledgers and separate disposable writer processes. No
hash-rule, schema, verifier, signer, concurrent-writer, authority, compliance,
adoption, or public-release change.

## Result

The append cache is safe for the observed process-local hot path when an
external writer changes the file size or modification time. An external
same-size replacement that preserves both cached metadata values is not
detectable by the current fingerprint. The next append then carries a stale
`prev` and the audit goes RED. That is a visible refusal, not silent acceptance,
but it is not support for concurrent writers.

Decision: **REPAIR-DESIGN-ONLY**. Keep the current bounded cache. Do not broaden
it or claim concurrent-writer support without an owner-approved design and
tests for file identity and timestamp-resolution behavior.

## Harness

- Windows 11, Python 3.13.2, local `src/` checkout.
- Each case used a fresh temporary root with two chained local claims.
- A child process performed the external mutation; the parent then appended
  through the cached path.
- The expected hash was independently read from the post-mutation last line
  before the cached append, serving as the full-scan baseline.
- The audit ran after the append. No customer, hosted, or private data was
  used.

## Raw invalidation matrix

| case | fingerprint changed | cached `prev` matched baseline | audit | records |
|---|---:|---:|---|---:|
| external append | yes | yes | GREEN | 4 |
| two rapid successive external writes | yes | yes | GREEN | 5 |
| truncate existing tip, then append | yes | yes | GREEN | 2 |
| same-size in-place replacement with original mtime restored | no | no | RED | 3 |
| same-size file replacement with original mtime restored | no | no | RED | 3 |

The same-size failures reported:

```text
chain break at line 3: prev is 8a3f84d8eb89..., matches no earlier line
(expected ae4d43523919...)
```

The truncate case also records a product boundary: deleting an unanchored
terminal record and then appending from its predecessor can remain GREEN. A
head published elsewhere would be needed to make that deletion detectable;
this report does not propose such anchoring.

## Recommendation

Retain the cache only as a process-local optimization with the existing full
scan fallback when `(st_size, st_mtime_ns)` changes. Keep audit as the authority
for chain integrity. Future design work may evaluate a stronger file identity
or explicit single-writer contract, but this fixture does not authorize either.

