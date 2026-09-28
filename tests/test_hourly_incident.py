"""Hourly skips cannot close a repair issue or generate repeated notifications."""
import importlib.util
import json
from pathlib import Path

import pytest


def reporter():
    spec = importlib.util.spec_from_file_location('hourly_incident',
        Path(__file__).resolve().parents[1] / 'scripts/report_hourly_integration.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exercise(admission='success', integration='failure', issues=None, ref='refs/heads/main'):
    module = reporter()
    calls = []
    def api(path, method='GET', payload=None):
        calls.append((path, method, payload))
        return (issues or []) if method == 'GET' else {'number': 42}
    result = module.report(api, 'owner/repo', 'a'*40, 17, ref, 'main', admission, integration)
    return result, calls


def test_failure_opens_one_issue_with_immutable_evidence():
    result, calls = exercise()
    assert result == 'created'
    assert calls[-1][1] == 'POST'
    assert 'a'*40 in calls[-1][2]['body']
    assert 'https://github.com/owner/repo/actions/runs/17' in calls[-1][2]['body']


def test_repeated_failure_is_quiet_and_new_commit_updates_same_issue():
    _, first = exercise()
    issue = dict(first[-1][2], number=42)
    assert exercise(issues=[issue])[0] == 'unchanged'
    issue['body'] = issue['body'].replace('a'*40, 'b'*40)
    result, calls = exercise(issues=[issue])
    assert result == 'updated'
    assert calls[-1][0].endswith('/issues/42')
    assert calls[-1][1] == 'PATCH'


@pytest.mark.parametrize('integration', ['skipped', 'cancelled'])
def test_skip_or_cancel_does_not_close_incident(integration):
    # REGRESSION: aggregate success on an hourly skip is not recovery evidence.
    result, calls = exercise(integration=integration)
    assert result == 'no-execution'
    assert calls == []


def test_admission_failure_is_actionable_unknown_coverage():
    result, calls = exercise(admission='failure', integration='skipped')
    assert result == 'created'
    assert 'admission failure' in calls[-1][2]['body']


def test_only_actual_success_closes_marked_issue():
    _, first = exercise()
    issue = dict(first[-1][2], number=42)
    result, calls = exercise(integration='success', issues=[issue])
    assert result == 'recovered'
    assert calls[-1][2]['state'] == 'closed'
    assert 'actions/runs/17' in calls[-1][2]['body']


def test_same_title_without_marker_or_pull_request_is_not_our_issue():
    module = reporter()
    issues = [{'number': 1, 'title': module.TITLE, 'body': 'unrelated'},
              {'number': 2, 'body': module.MARKER, 'pull_request': {}}]
    assert exercise(issues=issues)[0] == 'created'


def test_candidate_branch_cannot_change_default_branch_incident():
    assert exercise(ref='refs/heads/candidate') == ('non-default-branch', [])


def test_duplicate_incidents_and_api_failure_refuse_false_recovery():
    _, first = exercise()
    issue = dict(first[-1][2], number=42)
    with pytest.raises(RuntimeError, match='Multiple'):
        exercise(integration='success', issues=[issue, dict(issue, number=43)])
    def unavailable(*args, **kwargs):
        raise RuntimeError('API unavailable')
    with pytest.raises(RuntimeError, match='API unavailable'):
        reporter().report(unavailable, 'owner/repo', 'a'*40, 17, 'refs/heads/main',
                          'main', 'success', 'success')


def test_pagination_finds_existing_issue_instead_of_creating_duplicate():
    module = reporter()
    calls = []
    def api(path, method='GET', payload=None):
        calls.append((path, method, payload))
        if method != 'GET':
            return {}
        if path.endswith('&page=1'):
            return [{'number': n, 'body': 'unrelated'} for n in range(100)]
        return [{'number': 142, 'body': module.MARKER}]
    assert module.report(api, 'owner/repo', 'a'*40, 17, 'refs/heads/main',
                         'main', 'success', 'failure') == 'updated'
    assert calls[-1][0].endswith('/issues/142')


def test_api_transport_uses_fixed_host_authenticated_json_and_timeout(monkeypatch):
    module = reporter()
    monkeypatch.setenv('GH_TOKEN', 'fixture-token')
    observed = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"number":42}'
    def urlopen(request, timeout):
        observed.append((request, timeout))
        return Response()
    monkeypatch.setattr(module, 'urlopen', urlopen)
    assert module.api('repos/owner/repo/issues', 'POST', {'title': 'fixture'}) == {'number': 42}
    request, timeout = observed[0]
    assert request.full_url == 'https://api.github.com/repos/owner/repo/issues'
    assert request.method == 'POST'
    assert request.get_header('Authorization') == 'Bearer fixture-token'
    assert json.loads(request.data) == {'title': 'fixture'}
    assert timeout == 20


@pytest.mark.parametrize('sha,repo', [('main', 'owner/repo'), ('a'*40, '../repo')])
def test_invalid_execution_identity_fails_before_api_access(sha, repo):
    def forbidden(*args, **kwargs):
        raise AssertionError('API must not be used')
    with pytest.raises(ValueError):
        reporter().report(forbidden, repo, sha, 17, 'refs/heads/main',
                          'main', 'success', 'failure')
