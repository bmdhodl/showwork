# showwork build plan

## SW-04 opt-in pilot — 2026-09-21  [status: in progress]

- [x] Public pilot report form
- [x] Opt-in page; no cold outreach
- [x] Readout publishes 0/3 and 0/2; issue #64 is not an activation
- [ ] PR + second-model QA for #89 (no PyPI tag)

## SW-03 behavior quickstart — 2026-09-20  [status: merged]

- [x] Document fail / repair / rerun on Windows and Linux
- [x] Tests for refusal, recovery, and a fresh checkout
- [x] PR + second-model QA for #88 (no PyPI tag)

## SW-02 benchmark — 2026-09-18  [status: merged]

- [x] Freeze eight cases in `examples/sw-02-bench/`
- [x] Measure pytest, showwork, and Agent Verify 1.2.0
- [x] Label Agent Receipts and native hooks untested
- [x] Choose undeclared deletion as the measured advantage
- [x] PR + second-model QA for #87 (no PyPI tag)

## SW-01 CLI contract — 2026-09-18  [status: merged]

- [x] Reject `--absent` on `file_exists` and extra check keys at record time
- [x] Flag truth table in `docs/cli-check-flags.md`
- [x] Qualify pytest plugin, JS reader, and compliance wording
- [x] PR + second-model QA for #86

## v0.6.3 require flags — 2026-09-17  [status: published 0.6.3]

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
