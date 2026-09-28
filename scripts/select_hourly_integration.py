"""Select an hourly execution from existing Actions receipts, never a state file."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.request import Request, urlopen


def decide(runs, jobs_for_run, sha, current_run, *, force=False, complete=True, now=None):
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('An immutable full commit SHA is required')
    if force:
        return {'run': True, 'state': 'manual-force', 'evidence_run': None}
    failures = []
    uncertain_attempt = False
    now = now or datetime.now(timezone.utc)
    # Include rerun update times. A newer failed execution invalidates reuse of
    # an older pass at the same SHA until a fresh execution succeeds.
    for prior in sorted(runs, key=lambda row: (row.get('updated_at', ''), row['id']), reverse=True):
        if prior['id'] == current_run or prior['head_sha'] != sha:
            continue
        if prior['status'] != 'completed':
            return {'run': False, 'state': 'deferred-active', 'evidence_run': prior['id']}
        actual = [job for job in jobs_for_run(prior['id']) if job['name'] == 'integration']
        if len(actual) > 1:
            raise RuntimeError('Ambiguous integration job evidence')
        if len(actual) != 1 or actual[0]['status'] != 'completed':
            continue
        conclusion = actual[0]['conclusion']
        if conclusion == 'success' and prior['conclusion'] == 'success':
            if not failures and not uncertain_attempt:
                finished = datetime.fromisoformat(actual[0]['completed_at'].replace('Z', '+00:00'))
                age = (now - finished).total_seconds()
                if age < 0:
                    raise ValueError('Future execution evidence is not valid')
                if age >= 24 * 60 * 60:
                    return {'run': True, 'state': 'daily-refresh', 'evidence_run': prior['id']}
                return {'run': False, 'state': 'already-verified', 'evidence_run': prior['id']}
            break
        if conclusion in {'failure', 'timed_out'}:
            failures.append(prior['id'])
            if len(failures) == 2:
                return {'run': False, 'state': 'deferred-retry-limit', 'evidence_run': failures[0]}
        elif conclusion != 'skipped':
            uncertain_attempt = True
    else:
        if not complete:
            raise RuntimeError('History window is incomplete; use reviewed manual force, not an inferred retry')
    return {'run': True, 'state': 'needs-execution', 'evidence_run': failures[0] if failures else None}


def api(path):
    request = Request('https://api.github.com/' + path, headers={
        'Accept': 'application/vnd.github+json',
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'X-GitHub-Api-Version': '2022-11-28',
    })
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def history(repo, sha):
    # An API refusal is unknown history, not evidence of a first execution.
    data = api(f'repos/{repo}/actions/workflows/integration.yml/runs?per_page=100&head_sha={sha}')
    return data['workflow_runs'], data['total_count'] <= len(data['workflow_runs'])


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid repository identity')
    def jobs(run_id):
        data = api(f'repos/{repo}/actions/runs/{int(run_id)}/jobs?filter=latest&per_page=100')
        if data['total_count'] > len(data['jobs']):
            raise RuntimeError('Incomplete job evidence; selection refused')
        return data['jobs']
    sha = os.environ['GITHUB_SHA']
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('An immutable full commit SHA is required')
    runs, complete = history(repo, sha)
    result = decide(runs, jobs, sha, int(os.environ['GITHUB_RUN_ID']),
        force=os.environ.get('FORCE') == 'true', complete=complete)
    result['sha'] = os.environ['GITHUB_SHA']
    print(json.dumps(result, indent=2))
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as handle:
        handle.write(f"run={str(result['run']).lower()}\nstate={result['state']}\n")
    with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a', encoding='utf-8') as handle:
        handle.write('### Hourly admission (not a test result)\n\n```json\n'
                     + json.dumps(result, indent=2) + '\n```\n')
        handle.write('Coverage freshness comes from the last successful **integration** job, '
                     'not this admission timestamp or the overall workflow conclusion.\n')


if __name__ == '__main__':
    main()
