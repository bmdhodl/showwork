import importlib.util
from pathlib import Path

from showwork.ledger import record_claim, record_event, record_retraction


def replay(root):
    path = Path(__file__).resolve().parents[1] / 'scripts/replay_history.py'
    spec = importlib.util.spec_from_file_location('history_replay', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.replay(root)


def test_replay_checks_old_sessions_and_preserves_ledgers(tmp_path):
    (tmp_path / 'present.txt').write_text('real')
    record_claim(tmp_path, 'old', 'exists', {'type': 'file_exists', 'path': 'present.txt'})
    record_claim(tmp_path, 'new', 'missing', {'type': 'file_exists', 'path': 'missing.txt'})
    before = {p: p.read_bytes() for p in (tmp_path / '.showwork').rglob('*') if p.is_file()}
    state = replay(tmp_path)
    assert state['verdict'] == 'RED'
    assert state['passed'] == 1 and state['total'] == 2
    assert {r['session'] for r in state['results']} == {'old', 'new'}
    assert before == {p: p.read_bytes() for p in before}


def test_retractions_do_not_erase_acceptance_requirements(tmp_path):
    check = {'type': 'file_exists', 'path': 'missing.txt'}
    record_claim(tmp_path, 'old', 'missing', check)
    record_retraction(tmp_path, 'old', 'missing', 'withdrawn')
    record_event(tmp_path, 'session.requirement', 'old', requirement_id='proof',
                 claim='missing', scope='artifact', check=check, retracted=True)
    state = replay(tmp_path)
    assert state['verdict'] == 'RED'
    assert state['requirement_count'] == 1
    assert any(r.get('requirement_id') == 'proof' and r['status'] == 'fail' for r in state['results'])


def test_duplicate_requirements_fail_but_ids_are_session_scoped(tmp_path):
    (tmp_path / 'proof').touch()
    for session in ['one', 'two', 'one']:
        record_event(tmp_path, 'session.requirement', session, requirement_id='proof',
                     claim='proof', scope='artifact', check={'type': 'file_exists', 'path': 'proof'})
    state = replay(tmp_path)
    assert state['verdict'] == 'RED'
    assert state['passed'] == 2
    assert 'duplicate requirement' in state['results'][-1]['detail'] or any(
        'duplicate requirement' in r['detail'] for r in state['results'])


def test_empty_or_uncheckable_history_is_not_green(tmp_path):
    assert replay(tmp_path)['verdict'] == 'YELLOW'
    record_claim(tmp_path, 'old', 'unfalsifiable')
    assert replay(tmp_path)['verdict'] == 'YELLOW'


def test_malformed_requirement_cannot_disappear(tmp_path):
    record_event(tmp_path, 'session.requirement', 'old', requirement_id='bad',
                 claim='behavior', scope='behavior', check={'type': 'file_exists', 'path': 'proof'})
    assert replay(tmp_path)['verdict'] == 'RED'


def test_claim_and_requirement_share_output_but_not_verdict(tmp_path):
    root = tmp_path / 'repo'
    (root / 'scripts').mkdir(parents=True)
    counter = tmp_path / 'executions'
    (root / 'scripts/run_tests.py').write_text(
        'from pathlib import Path\n'
        f'p = Path({str(counter)!r})\n'
        'p.write_text(str(int(p.read_text()) + 1) if p.exists() else "1")\n'
        'print("passed")\n', encoding='utf-8')
    check = {'type': 'command', 'argv': ['python', 'scripts/run_tests.py'],
             'stdout_contains': 'passed'}
    record_claim(root, 'old', 'suite', check)
    record_event(root, 'session.requirement', 'new', requirement_id='suite',
                 claim='wrong assertion', scope='behavior',
                 check={**check, 'stdout_contains': 'absent'})
    state = replay(root)
    assert state['verdict'] == 'RED'
    assert [r['status'] for r in state['results']] == ['pass', 'fail']
    assert counter.read_text() == '1'
    assert state['results'][1]['evidence']['execution_reused'] is True


def test_corrupt_event_is_reported(tmp_path):
    events = tmp_path / '.showwork/sessions'
    events.mkdir(parents=True)
    (events / 'broken.jsonl').write_text('{broken\n', encoding='utf-8')
    state = replay(tmp_path)
    assert state['verdict'] == 'YELLOW'
    assert any(r['status'] == 'error' for r in state['results'])


def test_command_cannot_erase_requirements_during_replay(tmp_path):
    script = tmp_path / 'erase.py'
    script.write_text('from pathlib import Path\n'
                      'for p in Path(".showwork/sessions").glob("*.jsonl"): p.unlink()\n',
                      encoding='utf-8')
    record_claim(tmp_path, 'old', 'erase', {'type': 'command', 'argv': ['python', 'erase.py']})
    record_event(tmp_path, 'session.requirement', 'old', requirement_id='proof',
                 claim='missing proof', scope='artifact',
                 check={'type': 'file_exists', 'path': 'missing'})
    state = replay(tmp_path)
    assert state['verdict'] == 'RED'
    assert state['requirement_count'] == 1
    assert any(r.get('requirement_id') == 'proof' and r['status'] == 'fail' for r in state['results'])
    assert any(r['type'] == 'ledger-preservation' and r['status'] == 'fail' for r in state['results'])
