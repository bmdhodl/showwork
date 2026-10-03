# Acceptance review example, October 3, 2026

Issue [#95](https://github.com/bmdhodl/showwork/issues/95). Base:
`8ff8aec7c15312b9aca53a9a4af521629c4ee410`.

The [recipe](../acceptance-review.md) identifies the application write/read/reopen
contract, fixture inputs and expected labels before execution. The same acceptance
probe rejects an empty write and a cache-only implementation. A second process
reads application-produced output and never seeds missing output. Explicit
predicates remain active with Python optimization.

The implementation's initial absence failed three cases; an absent-file CLI check
was already negative. Optimization exposed three genuine false-pass controls
before repair. All seven focused cases passed after repair; the full Python suite
passed 659 tests. Raw output is retained alongside this report. These are authored
demonstrations, not a detection-rate estimate or independent real-failure corpus.

Fixture labels and tests are self-authored. Independent test adequacy review is
**not performed**. Maintainer review of the declared behavior, fixture inputs and
counterexamples remains the named adoption boundary. Human review effort is
unmeasured; no saved time, customer acceptance or full coverage is claimed.

No persisted showwork schema, automatic review score, provider call, release,
production BMD change or public campaign is included. The pytest adapter proposal
in #94 and October 13 decision in #92 remain separate, unresolved owner gates.

Receipt: `codex-acceptance-review-01a1000f`.
Sign-off: OpenAI | GPT-6 | auto.
