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
All 21 focused candidate, installed-smoke predicate and provenance controls passed.

Windows Python 3.10.11 and 3.13.2 are available locally. Linux clean installs,
the four-cell installed-wheel matrix and actual immutable artifact handoff have
not run at this point. The inactive workflow draft lives under `docs/ci/`, with
read-only permissions and no tag/upload/publisher steps. No guarded workflow,
credential, provider setting or schedule changed.

Raw [optimized failure controls](release-candidate-20261003/optimized-before.txt)
and [focused controls](release-candidate-20261003/focused.txt) are retained.
Current main at preparation start: `d41905b70f1fecf27872bd49c6fa36cee16b74f7`.

Sign-off: OpenAI | GPT-6 | auto.
