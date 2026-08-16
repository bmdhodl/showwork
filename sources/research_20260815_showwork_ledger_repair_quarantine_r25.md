# Showwork ledger repair quarantine — r25

Date: 2026-08-15  
Scope: receipt-maintenance only; no production code, parser, serializer, or SPEC change

## Finding

Before repair, `python -m showwork.cli audit --json` reported RED for the
append-only claims ledger: `888/921` records chained, `53` forks, and
`.showwork/claims-2026-08-15.jsonl` broken at line `398` with an unchained
record after the chain started.

The last intact snapshot is the claims file from commit `7b312bc`:

- 395 records
- final record hash: `3215d9d704f5b282580c6d5caa9b2d908ba48308d251a3f4096bc8dcb8d8b377`

The damaged correction suffix was observed in commit `77af2d7`. The raw torn
fragments are preserved here before the ledger is restored to the last intact
snapshot and corrected claims are re-appended serially.

## Quarantined bytes

Line 398, hash `3ff87772cdb64e72b3a7fe65999d098a6e16d562b947dd83840f48b0233e009f`:

```text
c8170433a77c55da88b98262041"}
```

Line 399, hash `0983df510d9fe59285c6124621decc17ad43262b1c5f8f058a82cd3f2e53cf44`:

```text
a88b98262041"}
```

Lines 396–397 and 400–403 were valid-looking records in the same damaged
correction suffix, but their `prev` links depended on the torn bytes. They are
not copied as ledger records. Their semantic evidence is represented again by
the new repair session after the intact snapshot is restored.

## Repair contract

`docs/concurrency.md` and the audit implementation establish that malformed or
unchained data after a chain has started is RED, and that recovery discards the
damaged fork rather than rewriting historical `prev` links or re-anchoring a
merge. This repair therefore removes only the damaged correction suffix from
the working ledger, preserves the exact bytes and commit history in this
quarantine record, and appends replacement claims through awaited, serial CLI
writes.

The external article
https://nblumhardt.com/2016/08/atomic-shared-log-file-writes/ is secondary
context only. It is not used as the repair authority or as production proof.

## Limits

This artifact does not claim a production concurrency fix, exact replay, signer
attestation, adoption, compliance, or human comprehension. It records a
scoped recovery of the local showwork receipt ledger so the repository gate can
be evaluated again.
