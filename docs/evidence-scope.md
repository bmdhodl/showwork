# What GolfFly showed us

The original GolfFly release animated a simulated brain. Its checks covered the
graphics and publication, but did not establish that measured neural connections
caused golf decisions. The credits disclosed the simulation. Broader claims
about the brain controlling the game were unsupported.

During the later model integration, another gap survived the checks. The model
chose a shot, but the putter handoff replaced its aim and distance. Code review
found it. A browser test through the real controller failed before the repair
and passed afterward. Tests of the model alone missed that downstream step.

The showwork records were weaker than their descriptions:

| Recorded claim | Actual check |
| --- | --- |
| Decisions use a measured graph | `m.weights` appears in a source file |
| Tests passed and HDR was verified | `2360` appears in a handwritten JSON file |

Both checks also passed against a fake file and a made-up count. No model, test
run or video was needed. The gate checked the supplied predicates, then displayed
the author's broader prose beside a passing mark. That was false assurance.

Three new claim files also remained uncommitted. The site did not run showwork
verification in CI. The installed verifier imported 0.4.0 source while package
metadata reported 0.2.0. Repeating the string example with 0.5.0 also passed, so
the stale install was a separate problem, not the cause of the scope failure.

## Declare the acceptance check

In 0.6.0 a default successful close requires declared acceptance checks. Declare
them before recording completion claims. Each requirement has an ID, a scope,
a description, and an executable check, appended to the existing session event
file. A claim retraction cannot remove a requirement.

```bash
showwork start --session shot-fix --agent codex
showwork require --session shot-fix --id shot --scope behavior \
  --description 'The club handoff preserves model aim and distance' \
  --check-json '{"type":"command","argv":["python","scripts/check_shot.py"]}'
showwork finish --session shot-fix
```

The script must exercise the actual controller and fail when it overwrites the
model output. A check that merely imports the model does not cover that behavior.
For an artifact requirement, use `--scope artifact` and a check that says exactly
what is observed, such as a file existing. Its result establishes no behavior.

Reports separately show individual checks, declared acceptance results, and the
number of behavior and artifact checks. Unlisted requirements remain unknown.
`finish --checks-only` records a limited close. It cannot pass `gate`.
YELLOW and disabled checks cannot certify a successful outcome.

## Ship the complete receipt

```bash
git add .showwork/ path/to/changed/files
git commit -m 'Preserve the model shot through club handoff'
showwork gate --session shot-fix --require-tracked
```

The close contains a manifest of claim files and a digest of requirements.
The gate checks the integrity chain, reruns acceptance checks, checks the latest
close, compares the manifest, and verifies receipt files against committed HEAD.
LF and CRLF checkouts are both supported. A missing claim file fails even when
a historical finish event says GREEN.
The selected session must have an intact chain. Historical unchained files are
reported as YELLOW separately; a broken chain anywhere still fails the gate.
Moving an old receipt out of its directory cannot hide its deletion.

The GitHub action can select every receipt changed by a PR:

```yaml
- uses: bmdhodl/showwork/actions/verify@v0.6.0
  with:
    changed-since: ${{ github.event.pull_request.base.sha }}
    require-tracked: 'true'
    allow-commands: 'true'
```

Use command execution only on trusted branches. The action defaults to refusing
repository commands and network access. Disabled behavior checks fail the gate.
Make the receipt job a required branch check; installing a hook does not do that.

`showwork doctor` prints the imported code version, installed package version,
module path, and interpreter. It exits nonzero when the versions disagree. Start
events and command evidence record the runtime version actually used.

## Reproduce and assess the limits

```bash
python examples/evidence_scope_demo.py
python -m pytest tests/test_outcomes.py -q
```

The demo checks three states: strings match but the close is refused; the actual
controller test fails; the controller is repaired and its test passes. Tests
also cover missing files in committed receipts, requirement retractions, disabled
execution, source changes during a test, and reopening a completed session.

Command evidence records hashes of stdout, stderr, the script and the source
tree, plus the exit code, Git revision, Python version and showwork version.
The source fingerprint has the existing snapshot bounds: generated directories,
symlinks, files over 32 MiB, and files beyond the 50,000-file limit are excluded.
Git worktree pointers, `.env.local`, and generated `.log` files are excluded too;
these machine-local files do not travel with a checkout. Check them explicitly
when their contents are part of the requested result.
It is not a full-machine or dependency attestation. Command checks execute trusted
project Python and are not sandboxed.

An author can still omit a requirement or write a useless test. The tool cannot
read the user's mind or prove that a test matches its description. It must not
claim that it can. Review the requirements and use negative cases that fail when
the reported behavior breaks. Hash chains preserve evidence; they cannot make
a weak test meaningful.
