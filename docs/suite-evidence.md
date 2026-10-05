# Offline suite evidence references

The owner selected the offline example-only scope on October 3, 2026 for
[#102](https://github.com/bmdhodl/showwork/issues/102),
[#103](https://github.com/bmdhodl/showwork/issues/103) and
[#70](https://github.com/bmdhodl/showwork/issues/70).
The [original proposal](suite-contract-proposal.md) records the reviewed boundary.
The October 13 business decision remains separate.

The caller supplies a local workspace, showwork session, requirement ID and full
selected revision, plus an AgentGuard trace and its existing JSON receipt. The
[example](../examples/suite/read_evidence.py) opens them independently. Its output
is an ephemeral display, not a supported SDK API or persisted join schema.
No correlation identifier is written back to either product.

## Existing vocabulary

| Concept | Existing reference | Meaning and limit |
| --- | --- | --- |
| Selection and permission | BMD selected card and owner authorization | Selects work and permitted operations; a receipt grants no fresh permission |
| Runtime observation | AgentGuard JSON receipt: trace/hash, counts, stops, version | Describes supplied trace bytes; absence of a stop does not prove complete interception |
| Decision observation | AgentGuard decision IDs, binding state and outcome | Records a decision; does not authorize another dispatch |
| Requirement | showwork `session.requirement`: ID, `claim` text, scope, check | Declared acceptance, not proof of adequate coverage |
| Source/config/input identity | Command `git_commit`, `script_sha256`, `source_sha256`, `source_scope`, optional exclusions | Identifies bounded recorded inputs; excluded or uncaptured inputs remain outside that scope |
| Artifact identity | Explicit named artifact check and referenced bytes/hash | Identifies the selected artifact; process exit does not establish usefulness |
| Integrity | Reader hash-chain audit and receipt manifest | Detects changed loaded bytes; provides no origin authentication |
| Freshness | Reader lifecycle plus supplied revision, runner and bounded source identities | Reopen, mismatch or changed source remains unverified; the view performs no Git discovery |
| Result | Recorded outcome and declared scope | Historical acceptance only; current execution remains unperformed |
| Evaluator provenance | Recorded command interpreter, version, source and output hashes | Describes the recorded evaluator, not an independent review or promotion decision |
| Human acceptance / promotion | Explicit owner decisions outside these receipts | Neither package infers these from process or check success |

Raw claims, trace content and command output stay in the user's workspace. The
local reader displays a selected requirement and hashed command references; it
does not implement a sharing endpoint. Any sharing needs an explicitly redacted,
reference-based summary. Stop details and recorded monetary values are omitted
from the example display.

## Display cases

| Input | Runtime row | Acceptance row / reference status |
| --- | --- | --- |
| Empty or missing | Unknown | Unknown |
| Prose without requirement proof | Independent if present | `claim_state: claimed`; acceptance unknown |
| No recorded runtime stop, failed test | No recorded stop | Failed work |
| Exhausted budget, unfinished requirements | Stopped | Incomplete; reference unbound |
| One passing artifact with unfinished work | Stopped if recorded | Remaining completion unverified |
| Intact matching close, artifact scope | Independent | Recorded verified artifact scope only |
| Artifact-only close without command metadata | Independent | Recorded artifact result; revision reference remains unknown |
| Intact matching close, behavior scope | Independent | Recorded verified declared behavior scope only |
| Reopen, source change or wrong revision/root | Independent | Incomplete or unknown; reference unknown |
| Missing, changed or incompatible runtime receipt | Unknown | Reference unknown even if acceptance has independent historical proof |
| Corrected retry | New trace reference | New result; original failed session retained |

For every case, `current_execution` remains `not performed`, `current_outcome`
remains `UNVERIFIED`, and `dispatch_authorized` is false. The display invokes no
checks, provider, network operation or ledger writer. An explicit active gate
belongs to a separately authorized operation.

Artifact-only checks do not record a command revision. Their intact historical
artifact result remains visible, while `reference_bound` is false and the join
stays unknown. Supplying a revision does not manufacture that missing binding.

## Compatibility and reproduction

| Consumer / producer | Pinned input | Tested boundary |
| --- | --- | --- |
| Python example | Source-built showwork wheel, metadata 0.6.6, with the reader and `snapshot-exclusions-v1` capability | Bounded loaded receipts, revision/runner/source matching, unknown references, no execution/write/network |
| AgentGuard producer | Source-built SDK wheel, metadata 1.4.1, source `45c4d54824319888abe67e3e437c38294c92a306` | `BudgetGuard.check` before a local provider stub, exported `build_receipt` JSON |
| Python and JavaScript readers | Same ten frozen fixtures in `tests/fixtures/readers` | Recorded fields, missing/reopened/tampered/incompatible evidence, no current execution |
| BMD display | Existing vault/frontmatter `verified`, `claimed`, `failed`, `unknown` contract; receipt owner BMD-008 | Interface review only; no showwork overlay is installed |
| PyPI showwork 0.6.5 and earlier | Earlier published artifacts | Do not supply these reader/exclusion features; 0.6.6 adds them |

The validation wheels are source-pinned and SHA-256 identified by the generated
proof. Their unchanged version metadata does not turn them into published
releases. The reader uses existing spec-v0.5 fields and the declared optional
exclusion capability; it introduces no ledger format or SDK API.

From this source checkout, with Python 3.10+ and Git:

```console
python scripts/check_suite_installed.py
python scripts/check_reader_conformance.py
```

The first command fetches the pinned public SDK source, installs build tools in
an isolated temporary environment and builds two validation wheels. Each runtime
installs only its own wheel. It runs local provider stubs, verifies denial before
another dispatch, failed and unfinished work, corrected artifact scope, retained
failure, wrong root/revision, missing runtime and incompatible version. It exits
nonzero on a broken check. No provider credentials or live provider requests are
used. For durable local inspection, `--artifacts NEW_DIRECTORY` retains the
generated workspace, separate environments, wheels and `proof.json`; an existing
directory is refused.

Use the reader with the installed validation wheel:

```console
python examples/suite/read_evidence.py WORKSPACE --session SESSION --requirement ID --revision FULL_SHA --trace runtime.jsonl --runtime-receipt runtime-receipt.json
```

Runtime files must be relative to that workspace and remain confined to it. The
fixture explicitly freezes `runtime-*` exclusions so trace writes do not change
the acceptance source identity. Its runtime hash check still runs independently.
The requirements and command evidence are visible in `.showwork/sessions/`.

This is synthetic compatibility proof, not outside adoption, a provider invoice,
complete interception, test adequacy, human usefulness or production BMD QA.
`check()` is a preflight check, not a concurrent reservation.

## BMD handoff

The existing BMD-008 receipt contract owns BMD run/artifact representation. The
[AgentGuard BMD boundary #744](https://github.com/bmdhodl/agent47/issues/744)
and owner-selected BMD roadmap own any future integration. The reviewed BMD
checkout (`2f209431a25be3208cdee5a91931b3bd37bda49f`) still uses its existing
vault/frontmatter interpretation in `lab/verification_badges.py`; it imports no
showwork overlay. Its `verified` label describes that existing contract and is
not interchangeable with a showwork declared behavior outcome. No BMD source,
ledger, dispatch, packaging or vault claims are
changed here. Any rendered BMD change needs its own selected task and real
Playwright proof on the designated test machine.

Public SDK sources: [receipt](https://github.com/bmdhodl/agent47/blob/45c4d54824319888abe67e3e437c38294c92a306/sdk/agentguard/receipt.py),
[guard](https://github.com/bmdhodl/agent47/blob/45c4d54824319888abe67e3e437c38294c92a306/sdk/agentguard/guards.py).

Sign-off: OpenAI | GPT-6 | auto.
