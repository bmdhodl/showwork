# showwork build plan

## v0.6.3 require flags — 2026-09-17  [status: in tree, owner-gated publish]

- [x] `require` uses the same check flags as `claim`
- [x] `--check-json` stays optional
- [x] README, Cursor walk, agent prompt, and Cursor rule declare require before claim
- [x] Advertised require lines have no JSON braces (PowerShell-safe)
- [ ] Owner: publish 0.6.3, tag `v0.6.3`, GitHub release
- [ ] Owner: post LinkedIn / X from `docs/reports/release-0.6.3/`

## v0.4.0 stranger onboarding — 2026-09-03  [status: released]

- [x] README quickstart refuses in an empty directory, then recovers
- [x] `python -m showwork` (`__main__.py`)
- [x] issue #64 undeclared delete/edit is RED (`spec-v0.4` tree snapshot)
- [x] `showwork init` for Cursor, Claude Stop hook, docs/ci draft
- [x] pytest plugin, opt-in `--showwork-session`
- [x] `docs/walks/cursor.md`, `docs/ci/verify.yml`, launch drafts
- [x] Owner: publish 0.4.0, tag, GitHub release

## BMD supervisor overlay — 2026-09-03  [status: in tree]

- [x] `showwork.receipts` read-only overlay (verified/claimed/failed/unknown)
- [x] `showwork receipts --json|--html`
- [x] Dispatch env + prompt helpers; no `--gate`
- [x] `examples/bmd/` pin, hiddenimports, copy-paste for the private BMD repo
- [x] Track remaining BMD work as a vault request (`docs/requests/bmd-overlay-receipts.md`), not GitHub Projects
- [ ] BMD repo: import overlay in `lab/verification_badges.py` (private; vault card is the tracker)

## v0.2 five phases — DONE (2026-07-16)

See git history / CHANGELOG 0.2.0.

## Exit criteria (0.6.3)

- [x] Full suite green
- [x] Session `cursor-require-flags-063` closed GREEN through the gate
