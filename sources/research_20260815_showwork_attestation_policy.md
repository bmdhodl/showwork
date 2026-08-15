# Research sources: public receipt policy boundary

Date: 2026-08-15

## Sources

- GitHub Artifact attestations: https://docs.github.com/en/actions/concepts/security/artifact-attestations
- Hardware-rooted attestation for AI-agent evidence: https://arxiv.org/abs/2608.00801
- Pipelab public proof and adversarial corpus discovery signal: https://pipelab.org/proof/
- Pipelab signed agent-action receipt discovery signal: https://pipelab.org/learn/verify-a-receipt/
- Signet cryptographic receipt discovery signal: https://github.com/Prismer-AI/signet
- Fresh adjacent GitHub Actions and agent-proof discovery signal: raw-byte receipt
  fixtures and deterministic action gates, supplied by the research watch on
  2026-08-15.
- Current evidence-packet market-coverage signal: receipt and verification
  practices are reinforced, but coverage does not establish showwork adoption.

## Comparison used in the fixture report

- GitHub's artifact attestations provide signed provenance and a public
  transparency-log path, but GitHub explicitly says an attestation is not a
  guarantee that the artifact is secure. This is a provenance and policy
  layer, not deterministic outcome verification.
- The AEP paper describes a software-layer action evidence package and states
  that it is necessary but insufficient when the question becomes model or
  hardware provenance. Its Attested, Contested, and Expired vocabulary is a
  useful comparison for policy labels, not a showwork verdict contract.
- Pipelab and Signet are public discovery signals for adversarial corpora,
  signed receipts, and offline verification. They are not evidence of
  showwork adoption and do not justify a second verifier, signing, hardware
  attestation, or framework adapter.
- The fresh adjacent-project signal reinforces two fixture properties already
  in scope: compare the exact public artifact bytes, and make the acceptance
  gate deterministic with explicit exit behavior. It does not add a new
  receipt format or verifier; the existing valid, mismatched, stale, and
  unverifiable local cases remain the single policy fixture.
- The market-coverage signal is recorded as corroboration for the proof
  boundary only. It does not change the four local cases or create evidence of
  an external user, integration, or framework adoption.

The local fixture remains offline and tests only the current showwork boundary:
chain audit plus deterministic re-checking of claims against current local
state.
