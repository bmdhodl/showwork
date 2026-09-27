# Claims audit - session claude-code-release-0.6.5-r2

**Check verdict: RED**  (8/10 checks passed)

**Outcome: UNVERIFIED**. Some acceptance checks or session checks did not pass.

Claim descriptions are author supplied. Results establish only the stated check.

- XX Check for claim: **pyproject version is 0.6.5** (`file_contains`, RED)
    - /^version = "0\.6\.5"/ NOT in pyproject.toml
- OK Check for claim: **module __version__ is 0.6.5** (`file_contains`)
    - /__version__ = "0\.6\.5"/ found in src/showwork/__init__.py
- OK Check for claim: **ARCHITECTURE names 0.6.5** (`file_contains`)
    - /__version__ = "0\.6\.5"/ found in ARCHITECTURE.md
- OK Check for claim: **README version line is 0.6.5** (`file_contains`)
    - /Version 0\.6\.5 binds the Claude Code Stop hook/ found in README.md
- OK Check for claim: **CHANGELOG 0.6.5 lists host-session binding** (`file_contains`)
    - /stamps .session_bound_from: host_session./ found in CHANGELOG.md
- OK Check for claim: **ci.md says mode ships in v0.6.5** (`file_contains`)
    - /ship in v0\.6\.5/ found in docs/ci.md
- OK Check for claim: **evidence-scope pins verify@v0.6.5** (`file_contains`)
    - /verify@v0\.6\.5/ found in docs/evidence-scope.md
- OK Check for claim: **handoff walk names showwork 0.6.5** (`file_contains`)
    - /This walk uses showwork 0\.6\.5/ found in docs/handoff.md
- XX Check for claim: **full suite passes at 0.6.5, including test_docs_pin_the_package_version and the release provenance tests** (`command`, RED)
    - exit 1, expected 0
- OK Check for claim: **CHANGELOG has a dated 0.6.5 section** (`file_contains`)
    - /## 0\.6\.5 - 2026-09-27/ found in CHANGELOG.md

## 2 gap(s) - a claimed 'done' is not real

- [RED/fail] pyproject version is 0.6.5 - /^version = "0\.6\.5"/ NOT in pyproject.toml
- [RED/fail] full suite passes at 0.6.5, including test_docs_pin_the_package_version and the release provenance tests - exit 1, expected 0

## Explanation

Observation: current_rerun. Historical finish: absent.
Check verdict: RED. Outcome: UNVERIFIED. Integrity: unknown.
Limitations: undeclared requirements: unknown; test adequacy: not assessed; formatting does not change the verdict.
Recovery: Repair the failed check, then rerun verify. This text does not authorize a merge or a clean close.
  requirement:absent check:file_contains scope:individual_check result:fail evidence:claim:0 revision:absent
       /^version = "0\.6\.5"/ NOT in pyproject.toml
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:1 revision:absent
       /__version__ = "0\.6\.5"/ found in src/showwork/__init__.py
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:2 revision:absent
       /__version__ = "0\.6\.5"/ found in ARCHITECTURE.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:3 revision:absent
       /Version 0\.6\.5 binds the Claude Code Stop hook/ found in README.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:4 revision:absent
       /stamps .session_bound_from: host_session./ found in CHANGELOG.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:5 revision:absent
       /ship in v0\.6\.5/ found in docs/ci.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:6 revision:absent
       /verify@v0\.6\.5/ found in docs/evidence-scope.md
  requirement:absent check:file_contains scope:individual_check result:pass evidence:claim:7 revision:absent
       /This walk uses showwork 0\.6\.5/ found in docs/handoff.md
  requirement:full suite passes at 0.6.5, including test_docs_pin_the_package_version and the release provenance tests check:command scope:behavior result:fail evidence:requirement:suite revision:cf8a9b79fb9c
       exit 1, expected 0
  requirement:CHANGELOG has a dated 0.6.5 section check:file_contains scope:artifact result:pass evidence:requirement:changelog revision:absent
       /## 0\.6\.5 - 2026-09-27/ found in CHANGELOG.md
