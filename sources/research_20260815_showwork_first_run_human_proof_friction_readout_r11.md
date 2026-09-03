# showwork first-run human proof friction readout r11

Date: 2026-08-15  
Scope: one clean disposable Python 3.13.2 venv, PyPI package, and synthetic
non-secret artifact. This is a first-run observation, not reliability,
customer-success, compliance, adoption, authority, signing, or reproducibility
evidence.

## Environment

- OS: Windows 11 build `10.0.26200`.
- Python: `3.13.2`, `C:\Python313\python.exe`.
- Venv creation: 5.940 seconds.
- `pip install showwork`: exit 0, 1.518 seconds, installed `showwork 0.3.0`.
- Proof root: `<temp>\showwork-first-run-r11-fff6b2c164994077bc2d23b5545f2ad4\proof-root`.
- Input: one synthetic `artifact.txt`; no customer or private data.

## Exact transcript

```text
start: exit 0, session.start recorded: first-run, 0.151s
claim: exit 0, claim recorded, 0.129s
verify --session first-run --json --no-report:
  exit 0, GREEN, 1/1, file_exists pass, 0.119s
finish --session first-run --status ok:
  exit 0, claims GREEN (1/1 verified), 0.118s
audit --json:
  exit 0, GREEN, 3 total / 3 chained / 0 forks, 0.123s
python scripts/evidence_pack.py (from proof root):
  exit 2, can't open file ...\scripts\evidence_pack.py, 0.052s
python K:\showwork\scripts\evidence_pack.py --root <proof-root> --from 2026-08-15 --to 2026-08-15 --framework all --out evidence-pack.md:
  exit 0, evidence pack written, 0.145s, 3,890 bytes
```

## Ranked friction

1. **Evidence-pack script location is not obvious after PyPI install.** The
   package CLI works, but the first pack command from the proof root failed
   because `scripts/evidence_pack.py` is repository-local. Recovery required a
   checkout path. This is the highest-friction step.
2. **Windows copy/paste mismatch.** The README quickstart uses Bash `\`
   continuation lines. A PowerShell first-run reader must adapt those commands
   before copy/paste.
3. **Version provenance is split.** PyPI installed 0.3.0, while the current
   local source checkout is 0.3.1. A reader can prove the synthetic claim, but
   must record which distribution or checkout supplied the command.

## What the run proves

It proves one local synthetic file predicate, a three-record intact chain, and
that a repository checkout can render an evidence pack. It does not prove the
truth of an external event, human approval, exact historical replay, legal
compliance, security certification, or adoption.

## One next action

Add a future release-gate fixture, without changing public copy in this task,
that runs the README proof path in a clean Windows shell and asserts: install
version is recorded, the minimal claim closes GREEN, `audit` is 3/3, and the
evidence-pack command is invoked from an explicit checkout path. The verifier
is the captured command exit/output transcript, not a claim of universal
first-run success.

## Decision

KEEP the current product surface and refusal language. NO CHANGE to package,
README, schema, verifier, or public copy follows from this single synthetic
run.
