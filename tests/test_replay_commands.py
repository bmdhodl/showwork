"""Historical replay shares execution, never assertion verdicts."""
import json

from showwork.checks import verify_claim


def fixture_command(tmp_path):
    root = tmp_path / 'repo'
    (root / 'scripts').mkdir(parents=True)
    counter = tmp_path / 'executions'
    script = root / 'scripts' / 'run_tests.py'
    script.write_text(
        'from pathlib import Path\n'
        f'p = Path({str(counter)!r})\n'
        'p.write_text(str(int(p.read_text()) + 1) if p.exists() else "1")\n'
        'print("passed")\n', encoding='utf-8')
    return root, counter, script


def record(needle='passed', exit_code=0):
    return {'session': 'history', 'claim': needle, 'check': {
        'type': 'command', 'argv': ['python', 'scripts/run_tests.py'],
        'expect_exit': exit_code, 'stdout_contains': needle}}


def test_shared_execution_preserves_each_assertion(tmp_path):
    root, counter, _ = fixture_command(tmp_path)
    cache = {}
    good = verify_claim(record(), root, command_cache=cache)
    wrong_text = verify_claim(record('absent'), root, command_cache=cache)
    wrong_exit = verify_claim(record(exit_code=7), root, command_cache=cache)
    assert [good['status'], wrong_text['status'], wrong_exit['status']] == ['pass', 'fail', 'fail']
    assert counter.read_text() == '1'
    assert good['evidence']['execution_reused'] is False
    assert wrong_text['evidence']['execution_reused'] is True
    assert good['evidence']['execution_id'] == wrong_exit['evidence']['execution_id']
    assert 'passed' not in json.dumps(good['evidence'])


def test_source_change_requires_new_execution(tmp_path):
    root, counter, script = fixture_command(tmp_path)
    cache = {}
    assert verify_claim(record(), root, command_cache=cache)['status'] == 'pass'
    script.write_text(script.read_text() + '# changed source\n', encoding='utf-8')
    result = verify_claim(record(), root, command_cache=cache)
    assert result['status'] == 'pass'
    assert result['evidence']['execution_reused'] is False
    assert counter.read_text() == '2'


def test_environment_change_requires_new_execution(tmp_path, monkeypatch):
    root, counter, _ = fixture_command(tmp_path)
    cache = {}
    assert verify_claim(record(), root, command_cache=cache)['status'] == 'pass'
    monkeypatch.setenv('SHOWWORK_REPLAY_FIXTURE', 'changed')
    assert verify_claim(record(), root, command_cache=cache)['status'] == 'pass'
    assert counter.read_text() == '2'


def test_default_verification_does_not_share_execution(tmp_path):
    root, counter, _ = fixture_command(tmp_path)
    assert verify_claim(record(), root)['status'] == 'pass'
    assert verify_claim(record(), root)['status'] == 'pass'
    assert counter.read_text() == '2'


def test_disabled_commands_cannot_reuse_pass(tmp_path, monkeypatch):
    root, counter, _ = fixture_command(tmp_path)
    cache = {}
    assert verify_claim(record(), root, command_cache=cache)['status'] == 'pass'
    monkeypatch.setenv('SHOWWORK_NO_COMMANDS', '1')
    assert verify_claim(record(), root, command_cache=cache)['status'] == 'error'
    assert counter.read_text() == '1'


def test_timeout_change_requires_new_execution(tmp_path, monkeypatch):
    root, counter, _ = fixture_command(tmp_path)
    cache = {}
    assert verify_claim(record(), root, command_cache=cache)['status'] == 'pass'
    monkeypatch.setenv('SHOWWORK_COMMAND_TIMEOUT_SECONDS', '121')
    assert verify_claim(record(), root, command_cache=cache)['status'] == 'pass'
    assert counter.read_text() == '2'


def test_other_script_invalidates_shared_suite(tmp_path):
    root, counter, _ = fixture_command(tmp_path)
    (root / 'other.py').write_text('print("done")\n', encoding='utf-8')
    cache = {}
    first = verify_claim(record(), root, command_cache=cache)
    assert first['status'] == 'pass'
    other = {'claim': 'other', 'check': {'type': 'command', 'argv': ['python', 'other.py']}}
    assert verify_claim(other, root, command_cache=cache)['status'] == 'pass'
    second = verify_claim(record(), root, command_cache=cache)
    assert second['status'] == 'pass'
    assert counter.read_text() == '2'
    assert first['evidence']['execution_id'] != second['evidence']['execution_id']
    assert first['evidence']['execution_input_sha256'] == second['evidence']['execution_input_sha256']


def test_source_mutation_during_execution_is_not_cached(tmp_path):
    root, counter, script = fixture_command(tmp_path)
    script.write_text(script.read_text() + 'Path("mutated.txt").write_text("changed")\n', encoding='utf-8')
    cache = {}
    result = verify_claim(record(), root, command_cache=cache)
    assert result['status'] == 'fail'
    assert 'source tree changed' in result['detail']
    assert cache == {}
