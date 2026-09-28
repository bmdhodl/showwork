"""Actions history is evidence only when the actual integration job passed."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest


SHA = 'a' * 40


def selector():
    spec = importlib.util.spec_from_file_location('hourly_selection',
        Path(__file__).resolve().parents[1] / 'scripts/select_hourly_integration.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(number, conclusion='success', sha=SHA, status='completed'):
    return {'id': number, 'head_sha': sha, 'status': status, 'conclusion': conclusion,
            'updated_at': f'2026-09-28T00:00:{number:02d}Z'}


def jobs(conclusion):
    return [{'name': 'integration', 'status': 'completed', 'conclusion': conclusion,
             'completed_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat()}]


def test_successful_actual_job_reuses_its_existing_receipt():
    result = selector().decide([run(9)], lambda _: jobs('success'), SHA, 10)
    assert result == {'run': False, 'state': 'already-verified', 'evidence_run': 9}


def test_reporter_failure_does_not_invalidate_successful_integration():
    # REGRESSION: an Issues API outage must not rerun passing tests every hour.
    result = selector().decide([run(9, 'failure')], lambda _: jobs('success'), SHA, 10)
    assert result == {'run': False, 'state': 'already-verified', 'evidence_run': 9}


@pytest.mark.parametrize('job_conclusion', ['skipped', 'cancelled', None])
def test_successful_workflow_with_no_passed_integration_does_not_prove_coverage(job_conclusion):
    # REGRESSION: an admission-only successful workflow is not a fresh test pass.
    result = selector().decide([run(9)], lambda _: jobs(job_conclusion), SHA, 10)
    assert result['run'] is True


def test_missing_history_runs():
    assert selector().decide([], lambda _: [], SHA, 10)['run'] is True


def test_other_commit_and_current_run_are_not_evidence():
    def forbidden(_):
        raise AssertionError('irrelevant run must not be inspected')
    assert selector().decide([run(10), run(9, sha='b'*40)], forbidden, SHA, 10)['run'] is True


def test_a_new_failure_after_a_pass_requires_a_retry():
    result = selector().decide([run(9, 'failure'), run(8)],
        lambda number: jobs('failure' if number == 9 else 'success'), SHA, 10)
    assert result['run'] is True


def test_two_failed_executions_defer_instead_of_retrying_forever():
    result = selector().decide([run(9, 'failure'), run(8, 'timed_out'), run(7)],
        lambda number: jobs('failure' if number != 7 else 'success'), SHA, 10)
    assert result == {'run': False, 'state': 'deferred-retry-limit', 'evidence_run': 9}


def test_cancelled_attempt_is_retried():
    assert selector().decide([run(9, 'cancelled')], lambda _: jobs('cancelled'), SHA, 10)['run'] is True


def test_active_equivalent_is_deferred_not_reported_as_tested():
    result = selector().decide([run(9, None, status='in_progress')], lambda _: [], SHA, 10)
    assert result['state'] == 'deferred-active'
    assert result['run'] is False


def test_explicit_manual_force_can_retest_the_same_commit():
    assert selector().decide([run(9)], lambda _: jobs('success'), SHA, 10, force=True)['run'] is True


def test_history_failure_cannot_become_a_skip():
    def unavailable(_):
        raise RuntimeError('Actions history unavailable')
    with pytest.raises(RuntimeError, match='unavailable'):
        selector().decide([run(9)], unavailable, SHA, 10)


def test_invalid_revision_is_refused():
    with pytest.raises(ValueError):
        selector().decide([], lambda _: [], 'main', 10)


def test_incomplete_history_cannot_reset_the_retry_budget():
    with pytest.raises(RuntimeError, match='incomplete'):
        selector().decide([run(9)], lambda _: jobs('skipped'), SHA, 10, complete=False)


def test_daily_refresh_uses_execution_time_not_skipped_tick_time():
    rows = jobs('success')
    rows[0]['completed_at'] = '2000-01-01T00:00:00Z'
    result = selector().decide([run(9), run(8)],
        lambda number: jobs('skipped') if number == 9 else rows, SHA, 10)
    assert result == {'run': True, 'state': 'daily-refresh', 'evidence_run': 8}


def test_new_successful_rerun_supersedes_later_created_failures():
    retried = {**run(7), 'updated_at': '2026-09-28T23:59:00Z'}
    result = selector().decide([run(9, 'failure'), retried],
        lambda number: jobs('success' if number == 7 else 'failure'), SHA, 10)
    assert result['state'] == 'already-verified'
    assert result['evidence_run'] == 7


def test_future_success_evidence_refuses():
    rows = jobs('success')
    rows[0]['completed_at'] = '2100-01-01T00:00:00Z'
    with pytest.raises(ValueError, match='Future'):
        selector().decide([run(9)], lambda _: rows, SHA, 10)


def test_ambiguous_job_evidence_refuses():
    with pytest.raises(RuntimeError, match='Ambiguous'):
        selector().decide([run(9)], lambda _: jobs('success') * 2, SHA, 10)


def test_cli_writes_admission_without_a_fresh_test_claim(tmp_path, monkeypatch):
    module = selector()
    paths = []
    def fixture_api(path):
        paths.append(path)
        if '/jobs?' in path:
            return {'total_count': 1, 'jobs': jobs('success')}
        return {'total_count': 1, 'workflow_runs': [run(9)]}
    monkeypatch.setattr(module, 'api', fixture_api)
    for key, value in {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_SHA': SHA,
                       'GITHUB_RUN_ID': '10', 'FORCE': 'false',
                       'GITHUB_OUTPUT': str(tmp_path / 'output'),
                       'GITHUB_STEP_SUMMARY': str(tmp_path / 'summary')}.items():
        monkeypatch.setenv(key, value)
    module.main()
    assert 'run=false' in (tmp_path / 'output').read_text()
    assert 'not a test result' in (tmp_path / 'summary').read_text()
    assert f'head_sha={SHA}' in paths[0]
