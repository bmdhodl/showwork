# Research sources: evidence-pack RED and unverifiable refusal

Date: 2026-08-15

## Existing paths exercised

- `scripts/evidence_pack.py`: `build_pack` refuses only when the chain audit is
  `RED`; otherwise it renders chain and claim verdicts into a pack.
- `tests/test_evidence_pack.py`: covers valid content, redaction, tampered-ledger
  refusal, and date filtering.
- `showwork audit` and `showwork verify --session`: provide separate integrity
  and current-claim signals.

## Temporary fixture observations

The runner created valid, mismatched, stale, tampered-ledger, and empty
unverifiable trees under a temporary directory and printed
`cleanup_verified: true` after the run.

- Valid: audit exit 0 GREEN 3/3; verify exit 0 GREEN 1/1; pack exit 0 and file
  written. The pack says chain GREEN 3/3, claims 1/1 GREEN, and receipt `OK`.
- Mismatched artifact: audit exit 0 GREEN 3/3; verify exit 2 RED 0/1; pack
  exit 0 and file written. The pack says chain GREEN 3/3, claims 0/1 RED,
  and receipt `XX`.
- Stale artifact: same bounded local outcome as the mismatched case: pack
  exit 0, file written, chain GREEN, claims RED 0/1, receipt `XX`.
- Tampered ledger: audit exit 2 RED; pack exit 2 and no file written. The
  refusal says evidence that cannot prove it was not edited is not evidence.
- Unverifiable empty tree: audit exit 3 YELLOW 0/0; verify exit 0 GREEN 0/0;
  pack exit 0 and file written. The pack says chain YELLOW 0/0 and claims
  GREEN 0/0. This is vacuous and must not be treated as proof.

Fresh search signals reinforce explicit verified/unverified receipt states but
do not establish showwork adoption. They do not change this fixture or justify
a second verifier, signing, hardware attestation, framework support, or a
public claim.

## Recommendation

NARROW CONSUMER-POLICY REPAIR: keep the packer unchanged in this pass, but
require consumers to see a non-empty closed session plus the audit verdict
before treating a pack as proof. Keep the existing RED-chain refusal. If a
future product request needs stronger behavior, add one acceptance test for
valid, mismatched, and unverifiable public artifacts before changing the
packer.
