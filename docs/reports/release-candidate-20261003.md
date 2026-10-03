# Release candidate preparation, October 3, 2026

This is an offline preparation packet for #104, not a released candidate or a
completed Windows/Linux compatibility matrix. The existing source metadata is
0.6.5; no compatible new version, tag or publishing authorization is selected.
The #92 October 13 continue decision and guarded workflow approval remain open.

The installed smoke script used Python assertions as acceptance predicates.
Three negative controls falsely passed with `python -O` before repair; the
matched fourth control passed. Explicit predicates now preserve those failures
under optimization. Eleven focused smoke/provenance tests passed after repair.
The full suite passed through strict finish (12/12 declared checks). The tracked
gate reruns that same behavior acceptance against the committed source.

The new candidate inspector reads existing evidence and prints a review packet.
Its tests use real temporary Git refs, bounded wheel metadata and controlled gate
JSON, including exact-byte retry after simulated partial success. It makes no
provider calls and neither simulates actual delivery as evidence nor publishes.
These fixture labels are self-authored; independent adequacy review is pending.
The initial 21 focused candidate, installed-smoke predicate and provenance controls passed.

Review found that the inspector's authored fixture used `command_evidence`
instead of the real gate result's `evidence` field. A real temporary session,
strict close, committed receipt and tracked gate reproduced the false refusal.
The inspector now consumes that actual output shape. Two additional controls
also failed before repair: contradictory top-level gate errors and a boolean
exit value. The repaired suite passed all 24 focused controls, including the
real tracked-gate path. Wheel metadata/hash and gate payload/hash now consume
the same bounded input bytes rather than separate reads.

The same local wheel built from `fd2a7665eb93e0953c1e57615f74cf0c72468742`
passed all 16 installed smoke checks under optimized Windows Python 3.10.11 and
3.13.2 in separate no-dependency venvs. Imported modules resolved under those
venvs, with no source path. Its SHA256 is
`328118ae0855aa66cda776b04a9d4e27b5c9f8de5f2f927fa9380b15b30c5549`.
This is an unpublished 0.6.5 test artifact, not the public PyPI wheel or a
candidate eligible to replace it. It predates the later native-host integration.
Linux clean installs and the complete four-cell matrix remain unperformed.
The inactive workflow draft lives under `docs/ci/`, with
read-only permissions and no tag/upload/publisher steps. No guarded workflow,
credential, provider setting or schedule changed.

Raw [optimized failure controls](release-candidate-20261003/optimized-before.txt)
and [focused controls](release-candidate-20261003/focused.txt) are retained.
[Real gate failure](release-candidate-20261003/real-gate-before.txt),
[contradictory-shape failures](release-candidate-20261003/shape-before.txt),
[repaired controls](release-candidate-20261003/review-after.txt),
[Windows 3.10 smoke](release-candidate-20261003/windows-py310.txt),
[Windows 3.13 smoke](release-candidate-20261003/windows-py313.txt) and
[wheel observations](release-candidate-20261003/wheel-observations.json) are retained separately.
Current main at preparation start: `d41905b70f1fecf27872bd49c6fa36cee16b74f7`.

Sign-off: OpenAI | GPT-6 | auto.
