# Proof-pack redaction leakage fixture — r26

Date: 2026-08-15  
Scope: disposable/local evidence; no pack-format or redaction-rule change  
Source checkout: `6e0355c`

## Fixture

The existing `scripts/evidence_pack.py::build_pack` path was run against a
disposable local ledger containing only synthetic values. Claim text included
secret-shaped tokens, Windows and POSIX paths, a private hostname and URL,
query parameters, an email address, an unlisted token-shaped value, and
ordinary public text. No real credential, private host, or published output was
used.

Redaction patterns were supplied by the fixture caller, matching the existing
packer contract. The packer scrubs rendered session and claim text; it does not
claim a general-purpose secret scanner.

## Matrix

| run | exit | size | observation |
|---|---:|---:|---|
| raw pack | 0 | 2701 bytes | synthetic sensitive-shaped values visible in rendered claim/session text |
| redacted pack | 0 | 2572 bytes | 129-byte reduction; listed token, paths, URL, and email were hidden |
| tampered ledger with redaction | 2 | refusal text | `REFUSED: the ledger's integrity chain is RED`; no pack is accepted |

The redacted pack retained `Chain audit verdict at export time: **GREEN**`
and the head table (`head (SHA-256, first 16)`), so the tested integrity
readout and file identity remained present. That is a fixture observation, not
a claim that redaction preserves every possible identity field.

## Leakage and over-redaction limits

- False negative: the unlisted `ghp_synthetic123` value remained visible when
  the caller did not provide a matching pattern.
- False positive: the broad `https?://[^ ]+` pattern also removed the ordinary
  public URL `https://showwork.example/docs`.
- Ordinary public claim text not matching a supplied pattern remained visible.
- A tampered first claim made the existing packer refuse with exit 2 because
  audit became RED. Redaction does not weaken the integrity gate.
- The packer’s caller-provided regexes are not a security certification,
  complete secret detector, privacy guarantee, or compliance proof.

## Reader-safe sharing guidance

Treat a generated pack as an operator-reviewed artifact. Use synthetic data for
fixture work, select narrow patterns for the actual fields in scope, inspect
the rendered output for residual paths/tokens/URLs, and preserve the integrity
refusal behavior. Do not infer public safety, adoption, or certification from a
GREEN disposable pack.

## Verification

- Existing evidence-pack tests: `python -m pytest tests/test_evidence_pack.py -q` -> `4 passed`.
- No source, parser, serializer, schema, public copy, release, or framework
  support changed.
