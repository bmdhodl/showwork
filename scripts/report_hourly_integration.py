"""Route scheduled failures through one existing GitHub issue, without local state."""
import json
import os
import re
from urllib.request import Request, urlopen


MARKER = '<!-- showwork-hourly-integration -->'
TITLE = '[CI] Hourly installed-package integration needs repair'


def report(api, repo, sha, run_id, ref, default_branch, admission, integration):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+', repo) or repo.split('/')[-1] in {'.', '..'}:
        raise ValueError('Invalid repository identity')
    if not re.fullmatch(r'[0-9a-f]{40}', sha) or int(run_id) <= 0:
        raise ValueError('Immutable execution identity required')
    if ref != 'refs/heads/' + default_branch:
        return 'non-default-branch'
    allowed = {'success', 'failure', 'cancelled', 'skipped'}
    if admission not in allowed or integration not in allowed:
        raise ValueError('Unknown job result')
    failure = admission == 'failure' or integration == 'failure'
    recovered = admission == integration == 'success'
    if not failure and not recovered:
        return 'no-execution'
    root = f'repos/{repo}/issues'
    issues = []
    for page in range(1, 101):
        rows = api(f'{root}?state=open&per_page=100&page={page}')
        issues.extend(row for row in rows if 'pull_request' not in row
                      and MARKER in (row.get('body') or ''))
        if len(rows) < 100:
            break
    else:
        raise RuntimeError('Incomplete issue history; refusing duplicate creation')
    if len(issues) > 1:
        raise RuntimeError('Multiple active integration incidents require reconciliation')
    existing = issues[0] if issues else None
    url = f'https://github.com/{repo}/actions/runs/{int(run_id)}'
    if recovered:
        if existing is None:
            return 'healthy'
        body = existing['body'] + f'\n\nRecovered by actual integration execution at `{sha}`: {url}\n'
        api(f"{root}/{existing['number']}", 'PATCH', {'state': 'closed', 'body': body})
        return 'recovered'
    kind = 'admission failure' if admission == 'failure' else 'integration failure'
    fingerprint = f'<!-- execution-failure:{sha}:{kind} -->'
    if existing and fingerprint in existing['body']:
        return 'unchanged'
    body = (f'{MARKER}\n{fingerprint}\n\n{kind.capitalize()} at `{sha}`.\n\n'
            f'Evidence: {url}\n\n'
            'Coverage is failed or unknown, not verified. Reproduce once, classify code versus '
            'infrastructure/configuration, and repair through a reviewed PR. The automatic '
            'execution retry is bounded; use manual force only after triage. '
            'Skipped admission ticks cannot close this issue.\n')
    if existing:
        api(f"{root}/{existing['number']}", 'PATCH', {'body': body})
        return 'updated'
    api(root, 'POST', {'title': TITLE, 'body': body})
    return 'created'


def api(path, method='GET', payload=None):
    request = Request('https://api.github.com/' + path, method=method,
        data=json.dumps(payload).encode('utf-8') if payload is not None else None,
        headers={'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'X-GitHub-Api-Version': '2022-11-28'})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def main():
    result = report(api, os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_SHA'],
        os.environ['GITHUB_RUN_ID'], os.environ['GITHUB_REF'], os.environ['DEFAULT_BRANCH'],
        os.environ['ADMISSION_RESULT'], os.environ['INTEGRATION_RESULT'])
    print('Hourly incident routing: ' + result)


if __name__ == '__main__':
    main()
