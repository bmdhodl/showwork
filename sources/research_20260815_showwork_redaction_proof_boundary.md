# showwork redaction proof boundary

Date: 2026-08-15
Scope: disposable synthetic fixture only. No ledger edit, hashing, signing,
public-copy, privacy guarantee, schema, or release change.

## Result

KEEP the existing `--redact` renderer as a presentation boundary, with a
clear limitation: it masks selected session and claim text in the exported
pack. It does not change the ledger, redact check arguments, add a redaction
manifest, or prove privacy. A redacted pack, a missing record, and an
unverifiable record must remain separate reader states.

## Fixture and commands

The fixture used synthetic strings only: session `redaction-fixture-SECRET-ALPHA`,
claim text containing `client@example.test` and `SECRET-ALPHA`, and an empty
`marker.txt` used by a `file_exists` claim.

```text
python -m showwork.cli --root <fixture> start --session redaction-fixture-SECRET-ALPHA --agent codex
python -m showwork.cli --root <fixture> claim --session redaction-fixture-SECRET-ALPHA \
  --claim "Synthetic client email client@example.test and token SECRET-ALPHA are fixture-only" \
  --type file_exists --path marker.txt
python -m showwork.cli --root <fixture> finish --session redaction-fixture-SECRET-ALPHA --status ok
python -m showwork.cli --root <fixture> audit --json
python scripts/evidence_pack.py --root <fixture> --from 2026-08-15 --to 2026-08-15 \
  --framework all --out pack-raw.md
python scripts/evidence_pack.py --root <fixture> --from 2026-08-15 --to 2026-08-15 \
  --framework all --redact 'client@example\.test' --redact 'SECRET-[A-Z]+' \
  --out pack-redacted.md
```

Observed results:

- Session verification: `GREEN (1/1 verified)`.
- Fixture audit: `GREEN`, 3/3 records chained, no forks.
- Raw and redacted packs both reported a `GREEN` chain and `1/1` claim
  verified at export time.
- The raw pack contained the synthetic session and claim strings. The
  redacted pack replaced those selected matches with `[redacted]`.
- The raw `.showwork` ledger still contained both synthetic strings after the
  redacted export. The renderer did not rewrite the ledger.
- An out-of-range export from the same intact fixture reported `GREEN (0/0)`
  with zero sessions and zero claims. That is an empty export, not proof that
  an event occurred.

## Field-by-field tradeoff

| Surface | Unredacted pack | Redacted pack | Boundary |
|---|---|---|---|
| Chain verdict and heads | Visible | Visible | Integrity of the retained ledger remains inspectable |
| Session and claim text | Visible | Selected regex matches become `[redacted]` | Reader cannot recover masked text from the pack alone |
| Check type and verification mark | Visible | Visible | The predicate and its export-time status remain reviewable |
| Check arguments and paths | May be exposed by the receipt inventory | Not generally masked by `--redact` | A regex over session/claim text is not whole-record sanitization |
| Raw ledger | Unchanged | Unchanged | A cleared party can still re-audit the original bytes |
| Missing event | No row or zero-session range | No row or zero-session range | Current pack has no positive missingness marker |
| Unverifiable event | RED claim mark, or RED chain refusal for tampering | Same verdict, subject to text masking | Redaction does not make a failed proof pass |

The [ARMO minimum viable audit trail guidance](https://www.armosec.io/blog/minimum-viable-audit-trail/)
describes source-boundary redaction and retaining shapes, sensitivity labels,
and hashes as a broader audit pattern. The current showwork option is narrower:
regex replacement in rendered session and claim text. It should not be described
as implementing that pattern or as a privacy control by itself.

## Decision

NO CHANGE. Keep `--redact` as an explicit export option and keep the pack's
scope warning. Do not add hashing, signing, redaction metadata, or privacy
claims from this synthetic fixture.
