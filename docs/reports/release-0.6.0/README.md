# showwork 0.6.0 verification

This release addresses the GolfFly evidence-scope failure described in
[the incident report](../../evidence-scope.md). The acceptance tests exercise
the verifier's behavior, not a text match on a handwritten success count.

| Requirement | Executable evidence |
| --- | --- |
| String matches cannot certify an outcome | `tests/test_outcomes.py::test_golffly_magic_strings_cannot_close_an_outcome` |
| The real controller must preserve the model output | `tests/test_outcomes.py::test_actual_controller_failure_then_repair` |
| Behavior cannot use an artifact check | `tests/test_outcomes.py::test_behavior_requirement_rejects_string_check` |
| Every declared requirement must pass | `tests/test_outcomes.py::test_one_pass_cannot_hide_an_unmet_requirement` |
| Retraction cannot remove acceptance requirements | `tests/test_outcomes.py::test_requirements_cannot_be_weakened_or_retracted_as_claims` |
| Missing claim files fail after a commit | `tests/test_outcomes.py::test_gate_detects_missing_claim_file_in_fresh_checkout` |
| Deleting a whole receipt cannot hide it | `tests/test_outcomes.py::test_deleted_entire_receipt_remains_in_changed_session_gate` |
| Disabled commands remain unverified | `tests/test_outcomes.py::test_disabled_command_never_certifies_behavior` |
| A source-changing test cannot pass acceptance | `tests/test_outcomes.py::test_acceptance_command_changing_source_fails` |
| Read-only badges never execute requirements | `tests/test_outcomes.py::test_read_only_requirement_does_not_run_python` |
| Windows receipts survive Linux checkout conversion | `tests/test_outcomes.py::test_windows_receipt_verifies_after_git_lf_checkout` |
| Empty, claimed and artifact states render correctly | `scripts/check_receipts_ui.py`, Chromium at 375, 768 and 1440 pixels |
| Full package behavior and ledger conformance | `scripts/run_tests.py` |
| JavaScript audit agrees with frozen chain fixtures | `scripts/check_js_conformance.py` |
| Installed package exposes the new gate and correct version | `scripts/smoke_release.py`, run with the installed interpreter |

The standalone demo has three assertions: string checks pass but outcome close
is refused; the controller test fails; the repaired controller passes. It does
not simulate a biological connectome or make claims about learning golf.

The GitHub clean-room workflow exercises the composite action against passing,
tampered, failed, unclosed, command-disabled, strings-only and missing-claim
receipts. The required receipt job gates the sessions changed by the PR.

Candidate evidence, GitHub job results, and public-package smoke are distinct
checks. A candidate result does not establish publication. Release assets carry
the actual public-install results after publication.

Sign-off: OpenAI | GPT-6 | auto
