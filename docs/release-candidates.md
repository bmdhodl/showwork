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

The current source metadata remains 0.6.5. A locally built 0.6.5 wheel is a test
artifact and must not replace the already published 0.6.5 distribution. A
compatible new version needs a separate owner-reviewed change. Recent bounded
reader and native-host capabilities are source changes until that publication.

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
