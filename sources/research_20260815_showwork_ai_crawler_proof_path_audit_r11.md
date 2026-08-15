# showwork AI-crawler proof-path audit r11

Date: 2026-08-15  
Retrieval: GitHub and PyPI pages read on 2026-08-15; local checkout and clean
venv transcript run on the same date. Scope is read-only. No public edit,
release, adoption, compliance, authority, signer, or universal reliability
claim is made.

## Discovery-to-proof map

| Step | Surface and evidence | Result | Boundary |
|---|---|---|---|
| Discover | [GitHub repository](https://github.com/bmdhodl/showwork) is public and titled “Make your AI agents show their work” | Identity and source are easy to find; README links SPEC and adapter docs | GitHub stars/forks are not adoption evidence |
| Install | [PyPI showwork](https://pypi.org/project/showwork/) presents `pip install showwork`; latest rendered release is 0.3.0, released 2026-07-18 | Package identity and install command are clear | PyPI package is not the current local source checkout |
| Minimal proof | GitHub/PyPI README quickstart: start, claim, finish | Commands are visible and deterministic | The README uses backslash continuation, which is Bash-oriented on Windows PowerShell |
| Inspect | README exposes `verify --session`, `verify --date`, and `audit`; SPEC is linked | Refusal and chain behavior are discoverable | Current verdict is bounded to recorded local predicates and ledger integrity |
| Render evidence | README/docs point to `scripts/evidence_pack.py` and `docs/compliance.md` | A checkout can generate a pack | The installed wheel does not put `scripts/evidence_pack.py` in a disposable proof root |
| Refuse overclaim | README says false closes are refused; compliance docs disclaim certification/legal sufficiency | Refusal boundary is documented | Do not infer authority, compliance, attestation, replay, or adoption |

## Clean first-run evidence

In a disposable Python 3.13.2 venv, `pip install showwork` installed 0.3.0 in
1.518 seconds after venv creation. One synthetic `file_exists` claim verified
GREEN, `finish` closed GREEN, audit reported 3/3 chained records, and the
repository checkout generated a 3,890-byte evidence pack. Running
`scripts/evidence_pack.py` from the proof root first failed with exit 2 because
the script is not installed there; pointing Python at the repository checkout
recovered successfully.

## Drift and one next action

The GitHub README CI example uses `bmdhodl/showwork/actions/verify@v0.3.0`,
while the rendered PyPI 0.3.0 description shows `@main`. This is release-time
documentation drift, not proof of a product failure.

One measurable next action: at the next owner-approved package release, run a
proof-path check that requires the rendered package description and GitHub
README to expose the same action ref, install command, and repository-checkout
path for `scripts/evidence_pack.py`; acceptance is exact link/ref parity plus
`python scripts/evidence_pack.py --help` exit 0 from the checkout. Do not make
that public edit in this task.

## Decision

KEEP the current proof/refusal boundaries and record this as a documentation
follow-up only. No README, PyPI, public copy, release, or adoption change
follows from one crawler/clean-run observation.
