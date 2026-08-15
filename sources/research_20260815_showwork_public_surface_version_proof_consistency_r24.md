# showwork public-surface version and proof consistency r24

Date: 2026-08-15  
Source revision: 6f55b4a  
Snapshot method: one read-only HTTP fetch per listed public surface. No public
copy, package, release, or adoption change.

## Snapshot

GitHub, the raw README, SPEC, CI docs, adapter docs, rendered PyPI, and PyPI
JSON all returned HTTP 200. The public package metadata reported version
`0.3.0`, Python `>=3.10`, two distribution files, and `-1` download sentinels
for day/week/month. The local checkout reports `0.3.1`; it is an unreleased
candidate and was not substituted for the public version.

| answer | public evidence | classification |
|---|---|---|
| version | PyPI JSON and rendered page report `0.3.0`; README badge points to PyPI | reproduced public fact |
| installation | README contains `pip install showwork` once; PyPI page is reachable | reproduced install instruction, not adoption |
| proof behavior | README names `showwork verify`, GREEN claims, and deterministic checks | documentation-only contract; not a fresh execution |
| false-close/refusal | README shows `REFUSED` and exit 2; adapter docs show the gate path | documentation-only refusal meaning; not a public run receipt |
| source/ledger location | GitHub links README, SPEC, CI, and adapter docs; SPEC contains spec-v0.2 integrity material | reproduced source location and contract links |
| adoption | no independent usage signal; download fields are `-1` and repository counters were not treated as usage | unknown |

The public surfaces were internally consistent at 0.3.0 for this snapshot.
The only version difference is between the public 0.3.0 artifacts and the
local 0.3.1 candidate. That is release state, not evidence that public pages
are contradictory.

## Boundary

Reachability, package indexability, visible commands, source links, and
documentation wording are separate from execution, traffic, install use, and
adoption. Any decision to publish 0.3.1 or update public copy is owner-gated.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
