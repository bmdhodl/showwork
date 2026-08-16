# Linked-worktree origin receipt identity — r27

Date: 2026-08-15  
Scope: report-only disposable Git repositories and worktrees; no change to
`resolve_root`, ledger files, real Git state, schema, adapter, or public copy.
 
Source card: `linked-worktree-origin-receipt-identity-readout-20260815-r27.md`

## Disposable evidence

The corrected fixture explicitly imported `K:\showwork\src\showwork`. It
created a temporary origin repository and a linked worktree, started one
session from each root, and recorded one checked claim from each root. Both
receipts resolved to the origin ledger:

| case | resolved root / ledger identity | observed result |
|---|---|---|
| origin root | temporary origin / `origin/.showwork/sessions.jsonl` | session id `origin-session` present |
| linked worktree root | same temporary origin / same ledger | session id `worktree-session` present; no worktree-local sessions ledger |
| after worktree removal | origin ledger remains | worktree absent, origin receipt still present, two records retained |

The session id is supplied by the caller and remains the identity key. Root
resolution determines where the receipt is stored; it does not prove who
operated the session or that two ids represent independent agents.

## Fork and failure matrix

After the two normal records, two synthetic session blocks re-anchored to one
earlier parent. The existing audit returned GREEN with one fork, two branch
heads, and no chain break. This is concurrent append evidence, not a single
linear history.

| case | result | reader-safe wording |
|---|---|---|
| origin/worktree receipt placement | origin ledger | “receipt is owned by the origin checkout; worktree deletion does not delete it” |
| concurrent branch append | GREEN, 1 fork, 2 heads | “integrity is intact with multiple heads; publish/compare each head separately” |
| origin renamed/unavailable | `RuntimeError` before write | “origin identity cannot be resolved; no receipt was claimed” |
| malformed `.git` worktree marker | `RuntimeError` before write | “Git metadata is malformed/unavailable; evidence is not verified” |

The unavailable-origin and malformed-metadata cases were temporary fixtures.
No recovery, re-chain, or history rewrite was attempted.

## Reader boundaries

For CI, humans, and AI readers, report the resolved origin path (or a stable
caller-supplied repository identity), ledger path, session id, and all current
branch heads. Do not collapse a compatibility `head` into proof that every
fork branch is represented. Worktree deletion proves only that the origin
receipt remains reachable in this local fixture; it does not prove backup,
remote durability, repository ownership, signer identity, or adoption.

## Portability and external evidence gaps

This evidence uses local Git behavior on Windows and the current Python
implementation. It does not establish behavior across Git versions, file
systems, network filesystems, CI checkout providers, permissions models, or
repository relocation. A missing origin is refused before writing, but no
portable recovery or external identity protocol is specified. Those gaps are
findings only.

Focused linked-worktree test: `1 passed, 9 deselected`; full suite: `241
passed`.

## Boundary

No source file, `resolve_root` behavior, receipt schema, ledger history,
adapter, signer, timestamp, release, public copy, or real Git checkout
changed.
