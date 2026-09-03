# Concurrent sessions and mergeable ledgers

showwork's ledger is a hash-chained, append-only log: every record carries
`prev`, the SHA-256 of the previous record line. A strictly linear audit is the
simplest way to prove append-only — but a strictly linear chain has exactly one
writer. Two agent sessions that append concurrently and later merge produce a
**fork**: two record blocks whose `prev` points at the same parent line. A
linear walk hits the second block and reports a chain break it cannot resolve.

## The failure we hit (2026-07-16, bmdhodl/bmdpat)

Two Claude Code sessions ran at once in separate git worktrees:

- Session A merged to `main` (PR #1061).
- Session B (`q3-consumer-pivot`, PR #1066) appended records to `sessions.jsonl`
  chaining off the parent line on `main`.
- Session A's worktree, still holding its pre-#1066 copy, appended further
  Stop-hook heartbeat records chaining off that **same** parent line.

When A's worktree branch merged, git union-merged `sessions.jsonl` into
`…parent, B-block, A-block`. A-block's first record still pointed at the parent,
not at B-block's tip. The audit went RED: `chain break at line 48`. Because the
ledger is append-only and rewriting `prev` is prohibited, the only resolution
was discarding A's forked lines (bmdpat PR #1065 closed unmerged).

That is the correct behavior for *tampering* and the wrong behavior for
*legitimate concurrency*. Both look identical to a linear walk.

## What we changed

Two boring, explicit pieces:

1. **Fork-tolerant audit.** A record is valid if its `prev` matches **any
   earlier line's hash** (or the genesis anchor), not only the immediate
   predecessor. A `prev` that re-anchors to a non-immediate earlier line is a
   *fork*, not a break. A `prev` that matches **no earlier line** is still RED,
   naming the exact line — because that is precisely what modification,
   deletion, and reordering produce.

2. **`.gitattributes` union merge.** `.showwork/**/*.jsonl` is marked
   `merge=union`, so git concatenates concurrent appends instead of writing
   conflict markers. Union preserves each side's line order, so every block's
   internal chain stays intact and each block re-anchors to the shared parent —
   exactly the shape the fork-tolerant audit accepts.

## Why this keeps the integrity guarantee

The guarantee showwork makes is **tamper-evidence**: modify, delete, or reorder
an *anchored* record and the audit names the break. Fork tolerance preserves
that exactly:

- **Modification.** Change any anchored line and its hash changes; every record
  that anchored to it now points at a hash matching no line → RED at the first
  such record. To hide it you must rewrite everything downstream, which moves
  the head(s).
- **Deletion of an anchored line.** The record that anchored to it points at a
  now-missing hash → RED.
- **Reordering.** An anchor must resolve to a line that appears **earlier** in
  the file. Move a record before its anchor and its `prev` no longer resolves
  backward → RED. Forks can only ever point *up* the file.

What fork tolerance gives up is **linearity**, not tamper-evidence: a file may
now hold more than one branch, so it has more than one *head* (tip). Deleting a
whole branch tip is undetectable from the file alone — but that was already true
of the single head in a linear chain (lopping off the last N records always
audited clean). The mitigation is unchanged and now applies per branch: the
audit reports **every head**, and publishing a head out-of-band (commit message,
post, printout) anchors that branch's tip. More heads to publish; the same math.

## Verdicts

| situation | verdict | exit |
|---|---|---|
| linear, intact | GREEN | 0 |
| forked, every `prev` resolves to an earlier line | GREEN, `forks=N`, heads listed | 0 |
| `prev` resolves to no earlier line (tamper/delete/reorder) | RED, break named | 2 |
| unchained record after the chain started | RED | 2 |
| records but no chain yet (spec-v0.1) | YELLOW | 3 |

A forked file is GREEN **on purpose**: that is what unblocks a legitimate
concurrent merge in CI. The fork is never silent — the count and every branch
head are printed, and the JSON carries `forks` and `heads`. A repo that never
runs concurrent sessions and wants strict single-history enforcement can pass
`showwork audit --strict`, which turns any fork RED.

## Why not the alternatives

- **Per-session ledger files** (`sessions/<id>.jsonl` and `claims/<id>.jsonl`)
  are the layout that scales with many agents. spec-v0.3 writes those files.
  Two agents with distinct slugs never share a path. Fork-tolerant audit
  remains for leftover shared files and for two writers that reuse one slug.
  It cannot un-RED a ledger that already merged a fork (bmdpat).
- **Silent `merge=union` as the scaler** concatenates concurrent appends into
  one file. That is a stopgap for leftover shared files, not the layout for
  many AIs. Two agents that share a slug still collide.
- **A re-anchoring merge driver** would rewrite `prev` on existing records,
  which the append-only contract prohibits.

## Operational guidance

- Give each agent a distinct session slug (`cursor-fix-nav`, `codex-fix-nav`).
- Commit `.showwork/` with the branch. Linked worktrees keep receipts in that
  worktree.
- After a leftover shared-file merge, `showwork audit` may show GREEN with a
  fork count. That is expected. `showwork audit --strict` forbids forks.
- Publish branch heads the same way you would publish a single head.
