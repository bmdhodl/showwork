# Package sdist README-target readiness — r27

Date: 2026-08-15  
Scope: local release preparation; no publish, tag, public-copy, or release-state change  
Baseline checkout: `6660cfb`

## Finding

The checkout metadata and source package version are `0.3.1`, while public
registry/tag evidence remains at `0.3.0`:

- `python -m pip index versions showwork`: latest `0.3.0`.
- GitHub tags: `v0.3.0`, `v0.2.0`, `v0.1.0`; no `v0.3.1` tag.
- `gh release list`: latest listed release `0.2.0`.

The first local `0.3.1` sdist build was healthy but omitted `SPEC.md`, the
`docs/` files and `scripts/` targets linked by `README.md`; its wheel installed
and reported `showwork 0.3.1`. This was a release-readiness defect, not a
registry or adoption claim.

## Change

Added `MANIFEST.in` rules for the portable specification, README-linked docs,
scripts, action metadata, JavaScript auditor, tests, and release metadata. The
manifest excludes Python caches. Added a behavioral test that builds an sdist
and asserts the README targets are present without `__pycache__` or bytecode.

Post-fix evidence:

- sdist: `127740` bytes; `SPEC.md`, `docs/ci.md`,
  `docs/claude-code.md`, `scripts/evidence_pack.py`, and
  `js/showwork-audit/index.mjs` present.
- Wheel install in a fresh local venv: `showwork.__version__ == 0.3.1`.
- Sdist install in a disposable system-site-packages venv:
  `showwork.__version__ == 0.3.1`.
- Packaging test: `python -m pytest tests/test_packaging.py -q` -> `1 passed`.

## Owner gate and limits

PyPI publication, Git tagging, release creation, and public documentation
version updates remain owner-gated and were not performed. `docs/ci.md` still
describes the currently published action ref `@v0.3.0`; it must not be changed
to imply that `0.3.1` is public before the owner releases it.

This artifact proves local build/package readiness only. It does not prove
registry availability, adoption, traffic, compatibility across external
installers, supply-chain trust, or release completion.
