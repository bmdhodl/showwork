# Research sources: AI-query coverage of the public proof path

Date: 2026-08-15

## Query map

| Query class | Direct source | Answerable? | Unsupported or ambiguous claim |
| --- | --- | --- | --- |
| install | `README.md` install section; https://pypi.org/project/showwork/ | yes | public package availability is not adoption |
| what does it prove? | `README.md` model; `SPEC.md`; `docs/compliance.md` | yes with limits | it does not prove authorship, hardware provenance, or outside witnessing |
| what happens on tampering? | `showwork audit`, `SPEC.md`, `docs/concurrency.md` | yes | a fork is not tampering; strict mode changes policy |
| what happens when state goes stale? | `docs/compliance.md` export-time section; attestation report | yes | intact chain does not make a stale claim current |
| how are forks handled? | `README.md`, `docs/concurrency.md`, audit JSON | yes for CLI | rendered evidence packs omit fork-head detail and source provenance |
| how does CI use it? | `README.md`, `docs/ci.md`, `.github/workflows/clean-room-action.yml` | yes | clean-room fixtures are not external integrations |
| what is exposed privately? | `docs/compliance.md` redaction section and evidence-pack disclaimer | partial | the docs describe redaction, not a guarantee about every consumer's handling |
| is it adopted? | public-proof/adoption report; live GitHub/PyPI signals | yes: not established | stars, clones, downloads, forks, and AI mentions cannot prove adoption |

## Adjacent comparison

[agent-receipts](https://github.com/inchwormz/agent-receipts) makes an explicit
`unverified` state and separates integrity, outcome, applicability, and claim
status. [Proof Agent](https://github.com/marketplace/actions/proof-agent-verify)
describes separate worker/verifier roles with PASS/FAIL/PARTIAL labels, and its
public method says the verifier reviews diffs without executing code or tests.
These are useful answer-shaping signals only. They do not prove showwork
adoption and do not authorize a second verifier or framework support.

## Recommendation

NO CHANGE to public docs or product surface. The current sources answer the
eight questions when read together, and the existing reports carry the
unverifiable/adoption caveats. The prioritized content gap is discoverability:
the minimum safe proof bundle is split across README, concurrency, compliance,
and research reports.

A future public edit would require a real attributable reader question or
repeated support ambiguity about those fields. GitHub/PyPI traffic, AI crawler
mentions, owner fixtures, and adjacent projects are not that measurement.
