# Release candidate review

Issue #104 is preparation for an owner-reviewed candidate. The October 13
continue decision on #92, workflow approval, a compatible new version and a
complete Windows/Linux install matrix remain gates. No schedule, tag, upload,
publisher permission or owner policy changes with this packet.

`scripts/inspect_candidate.py` is a read-only local inspector. It checks a clean
source tree at a caller-supplied full revision equal to fetched `origin/main`,
base ancestry, source version, one bounded wheel's package metadata and SHA256,
and the existing gate JSON's GREEN / VERIFIED behavior evidence at that revision.
It never executes commands from the gate file. A candidate is for review;
`publication_authorized` is always false. Hashes identify supplied bytes, not
authentic producer identity, adequate tests or a wheel's source provenance.

Prepare evidence from an already reviewed main revision. Keep build outputs and
raw gate results outside the checkout so the source remains clean. Use the
repository's Python environment for the behavioral gate and a separate clean
venv for each installed wheel smoke. The installed environment must not carry
`PYTHONPATH` or an editable/source installation.

```text
python -m showwork gate --session REVIEWED_SESSION --require-tracked --json
python -m build --wheel --outdir OUTSIDE_CHECKOUT
python scripts/inspect_candidate.py --reviewed-sha FULL_SHA --base-sha PRIOR_REVIEWED_SHA --version SOURCE_VERSION --wheel EXACT_WHEEL --gate CAPTURED_GATE_JSON --accepted-change
```

Capture gate output with a UTF-8 writer appropriate to the shell. Shell
redirection on Windows PowerShell 5.1 can write UTF-16, which is not the JSON
encoding accepted by the inspector. The input gate is local evidence, not a
signature or substitute for inspecting the actual CI gate and source review.

The owner reviews accepted changes, compatibility, the proposed version,
changelog, exact wheel hashes, receipt scope, test adequacy and clean installs
on Python 3.10 plus a current supported Python on Windows and Linux. Include
JS reader conformance and the installed negative smoke: broken acceptance
must refuse, repair must pass, empty completion and timeout must fail. The
smoke's explicit predicates remain active with `python -O`.

The current source metadata is 0.6.6. A locally built 0.6.6 wheel is a test
artifact and must not replace the published 0.6.6 distribution. A new version
needs a separate owner-reviewed change.

## Claims a version bump replaces

A version bump makes each claim that pins the old version false. CI's
`showwork verify` checks every claim dated with the current UTC date, so a
claim recorded on the day of the bump turns `main` RED. On 2026-10-05 the
0.6.6 bump did this to a claim that ARCHITECTURE.md names 0.6.5. A claim's
`ts` uses the writer's local clock, so its date can differ from CI's date.

Before the release session finishes, verify CI's date and your local date:

```text
python -c "import datetime; print(datetime.datetime.now(datetime.timezone.utc).date())"
python -m showwork verify --no-report --date UTC_DATE
python -m showwork verify --no-report
```

For each failed claim of another session that the bump replaced, record
`showwork supersede --session RELEASE --target-session OTHER --claim "EXACT
TEXT" --reason "the X.Y.Z bump moves FILE to X.Y.Z"`. Do not retract it: a
retraction changes that session's closed receipt. Repair a failed claim that
the bump did not replace; it is a real regression. The follow-up change that
moves `actions/verify@vX.Y.Z` pins to the new tag does the same for claims
that pin the old tag. Claims from earlier days keep their actual result in
the nightly historical replay.

Release claims must not pin the new version either, because the next bump
makes them false. `test_current_version_lines_follow_package_metadata` in
`tests/test_documentation.py` reads the version from `pyproject.toml` and
checks each line that states the current version. The `regression`
requirement (`scripts/run_tests.py`) runs it, so that requirement backs a
claim that the documents name the current version.

## No release and retry

Omit `--accepted-change`, or supply an identical base and reviewed revision,
to produce `no-release` with artifact checks explicitly not performed. The
flag records the caller's selection; it cannot establish meaningfulness or
owner consent. No weekly version bump follows from elapsed time alone.

The [inactive workflow draft](ci/weekly-candidate-review.yml) serializes candidate
attempts. It is outside `.github/workflows/` and has no publishing step. Applying
it needs the owner authorization required by the vault's guarded-path rules.

After partial publication, keep the original immutable artifact and use
`--retry-sha256 APPROVED_WHEEL_SHA256` to refuse different bytes. The inspector
does not track or resume a remote operation. Before any authorized retry, read
back each remote artifact, version, hash and provider status; confirm which
steps succeeded and retain uncertainty. Never rebuild different bytes under
one version, infer success from an upload attempt, overwrite a released artifact
or activate automatic retries. Existing publication concurrency remains separate.

## Retained controls

The candidate tests use real temporary Git refs and bounded wheel metadata,
including failed gate, wrong revision/version, missing wheel, stale candidate,
dirty source, wrong wheel identity, exact-byte retry and no-release. Those
controlled inputs are not real publication or platform-install evidence.

The installed smoke had three false-pass cases under optimized Python before
its repair: wrong exit, RED verification and unknown receipt state. The fourth
matched control passed. [Raw failing controls](reports/release-candidate-20261003/optimized-before.txt)
are retained. Tests now use explicit predicates instead of removable assertions.

Current preparation results and unperformed platform checks belong in the
[dated report](reports/release-candidate-20261003.md). #104 stays open until its
matrix, approved workflow and dated prerequisites are satisfied.
