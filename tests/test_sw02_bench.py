"""SW-02 eight-case bench: replay pytest and showwork verdicts."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "docs" / "reports" / "sw-02-benchmark" / "results.json"
REPORT = ROOT / "docs" / "reports" / "sw-02-benchmark" / "README.md"
SEED = ROOT / "examples" / "sw-02-bench" / "seed"

spec = importlib.util.spec_from_file_location(
    "sw02_bench", ROOT / "examples" / "sw-02-bench" / "run.py"
)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def _results() -> dict:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def test_sw02_seed_is_the_public_fixture():
    for name in ("add.py", "config.txt", "bystander.txt", "test_add.py", "run_tests.py"):
        assert (SEED / name).is_file()
    assert "timeout: 30" in (SEED / "config.txt").read_text(encoding="utf-8")
    assert "keep this file" in (SEED / "bystander.txt").read_text(encoding="utf-8")


def test_sw02_frozen_cases_are_exactly_eight():
    assert bench.CASES == (
        "honest-pass",
        "honest-fail",
        "never-run-test",
        "weak-fixture",
        "undeclared-deletion",
        "stale-revision",
        "missing-receipt",
        "cross-client-handoff",
    )
    assert set(bench.EXPECTED) == set(bench.CASES)


def test_sw02_replay_matches_frozen_verdicts(tmp_path, monkeypatch):
    monkeypatch.delenv("SW02_AGENT_VERIFY", raising=False)
    out = tmp_path / "results.json"
    assert bench.main(["--out", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["denominator"]["cases"] == 8
    assert payload["denominator"]["cases_matching_expected"] == 8
    for name, expected in bench.EXPECTED.items():
        assert payload["cases"][name]["observed"] == expected
        assert payload["cases"][name]["agent_verify"]["status"] == "untested"


def test_sw02_committed_results_keep_frozen_verdicts():
    payload = _results()
    assert payload["denominator"]["cases_ran"] == 8
    assert payload["denominator"]["cases_matching_expected"] == 8
    for name, expected in bench.EXPECTED.items():
        row = payload["cases"][name]
        assert row["expected"] == expected
        assert row["observed"] == expected
        assert row["match"] is True


def test_sw02_undeclared_deletion_is_the_measured_advantage():
    """REGRESSION: pytest-only or tests-only tools stay green on a bystander delete."""
    payload = _results()
    row = payload["cases"]["undeclared-deletion"]
    assert row["observed"]["pytest_after"] == 0
    assert row["observed"]["showwork_finish"] == 2
    assert payload["advantage"]["id"] == "undeclared-deletion"
    av = row["agent_verify"]
    if av["status"] == "ran":
        assert av["exit"] == 0
    report = REPORT.read_text(encoding="utf-8")
    assert "Undeclared deletion" in report
    assert "Keep the snapshot gate" in report


def test_sw02_weak_fixture_is_human_reviewed():
    payload = _results()
    row = payload["cases"]["weak-fixture"]
    assert row["adequacy"] == "human-reviewed"
    assert row["observed"]["pytest_exit"] == 0
    assert row["observed"]["showwork_finish"] == 0
    assert row["observed"]["production_stdout"] == "5"
    report = REPORT.read_text(encoding="utf-8")
    assert "human-reviewed" in report
    assert "cannot detect that omission" in report


def test_sw02_never_run_artifact_close_is_false_green():
    payload = _results()
    row = payload["cases"]["never-run-test"]
    assert row["adequacy"] == "false-green"
    assert row["observed"]["pytest_if_run"] == 1
    assert row["observed"]["showwork_artifact_finish"] == 0
    assert row["observed"]["showwork_behavior_finish"] == 2
    av = row["agent_verify"]
    if av["status"] == "ran":
        assert av["exit"] == 1
    report = REPORT.read_text(encoding="utf-8")
    assert "That is not a showwork win" in report


def test_sw02_report_labels_untested_hosts_and_versions():
    payload = _results()
    for key in (
        "agent_receipts",
        "github_actions_job",
        "claude_code_stop_hook",
        "cursor_hooks",
        "codex_native_hooks",
    ):
        assert payload["untested"][key]["status"] == "untested"
    assert payload["versions"]["showwork"]
    assert payload["versions"]["pytest"]
    report = REPORT.read_text(encoding="utf-8")
    assert "untested" in report
    assert "Agent Receipts" in report
    assert "No PyPI tag is authorized" in report


def test_sw02_results_are_not_a_live_native_hook_run():
    payload = _results()
    assert "not a Claude Code" in payload["untested"]["claude_code_stop_hook"]["reason"]
    assert payload["untested"]["agent_receipts"]["claimed_version"] == "0.2.0"
