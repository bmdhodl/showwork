# Reading a receipt without execution

`showwork.reader.inspect_session(workspace, session)` and
`inspectSession(workspace, session)` from `js/showwork-audit/index.mjs` inspect
recorded evidence. Both use the supplied workspace directly. Neither discovers
Git, starts Python or another process, makes network requests, or writes files.
An explicit CLI invocation starts its interpreter; `showwork receipts` does not
start child processes.

```python
from showwork.reader import inspect_session
receipt = inspect_session("/workspace/project", "task-123")
print(receipt["integrity"], receipt["recorded_outcome"], receipt["current_outcome"])
```

```javascript
import { inspectSession } from "./js/showwork-audit/index.mjs";
const receipt = inspectSession("/workspace/project", "task-123");
console.log(receipt.integrity, receipt.recorded_outcome, receipt.current_outcome);
```

| Capability | Python inspector | JavaScript inspector | Python receipt overlay |
| --- | --- | --- | --- |
| Reading fields from spec-v0.1 through spec-v0.5 | Yes | Yes | Yes |
| Existing hash chain, forks and legacy layout | Yes | Yes | Yes |
| Requirement inventory and scope | Recorded | Recorded | Recorded plus allowed observations |
| Close manifest hashes and count | Compared | Compared | Compared |
| Frozen snapshot-exclusions-v1 scope and sidecar | Validated and disclosed | Validated and disclosed | Validated and disclosed |
| Reopened session or missing/changed manifest | UNVERIFIED | UNVERIFIED | Cannot show a verified outcome |
| Current filesystem checks | None | None | file_exists, path_moved, frontmatter, glob_count |
| Current snapshot damage check | None | None | Existing Python checker and bounds |
| Regex, command, Git or network checks | Never run | Never run | Disabled, outcome unknown |
| Future required semantics or unknown lifecycle event | Unsupported | Unsupported | UNKNOWN |
| Test adequacy, complete user requirements, authentic origin | Not established | Not established | Not established |

These are reading capabilities, not full verifier conformance. The inspectors
return `current_execution: not performed` and `current_outcome: UNVERIFIED` even
when an intact committed history records a verified finish. The manifest
comparison establishes that the loaded claim definitions match the recorded
close. It does not prove who authored them, that a test was adequate, or that the
workspace still behaves that way. No current Git revision is discovered; revision
freshness requires an explicit active gate at the revision the reviewer selects.

The Python overlay retains supported filesystem observations through the
existing checker, with an explicit filesystem-only observation label. It requires
a matching successful outcome close before showing VERIFIED. A command or regex
worker check stays UNKNOWN until an authorized caller explicitly runs the active
verifier. A file observation cannot establish behavior.

The supported reading fields are `session`, `retracts`, `event`, `ts`, requirement
IDs/scopes/check descriptions, close `status`, `completion_scope`, `outcome`,
`verify_bypassed`, and `receipt_manifest`. Optional `spec_version` declarations
outside the listed versions and unknown nonempty `required_semantics` are unsupported.
The source readers support `snapshot-exclusions-v1` on session starts, validate
its frozen snapshot sidecar and disclose `snapshot_scope`. This capability ships
in showwork 0.6.6. Readers that lack it cannot qualify such a receipt.
See [explicit snapshot exclusions](snapshot-exclusions.md) for the matching
rules, compatibility boundary and new-file coverage limit.
Unknown required events are unsupported. Unknown optional prose is not promoted
to evidence. Malformed JSON and duplicate keys are unreadable. Missing close
fields leave recorded acceptance UNVERIFIED. Unknown check types and requirement
scopes are unsupported.

Receipts remain in the existing single-writer per-session layout. Readers also
recognize legacy shared JSONL files. Paths must resolve inside the supplied
workspace. Reads stop at 4 MiB per file, 32 MiB total and 1,024 ledger files; a
limit failure is unknown. This adds no ledger format, storage service or runtime
dependency. Snapshot traversal retains the reference checker's existing limits.

Frozen bytes and expected shared labels live in `tests/fixtures/readers/`.
Run `python -m pytest tests/test_readers.py -q` and
`python scripts/check_reader_conformance.py`. Browser verification is
`python scripts/check_receipts_ui.py` at 375, 768 and 1440 pixels.

The [offline suite example](suite-evidence.md) reads the same fields beside an
AgentGuard JSON receipt. It additionally compares supplied revision, runner and
bounded source identities, without discovering Git HEAD or running a check. Its
ephemeral display grants no dispatch authority and introduces no SDK API or
persisted join. Installed source-built wheel proof is reproduced with
`python scripts/check_suite_installed.py`; package publication remains separate.
