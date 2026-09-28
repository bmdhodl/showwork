"""The CI entry point must execute the suite through genesis exactly once."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_driver():
    spec = importlib.util.spec_from_file_location('ci_genesis', ROOT / 'scripts/check_ci_genesis.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, *, code=0, output='passed', missing_readme=False):
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts/run_tests.py').write_text(
        "from pathlib import Path\np=Path('calls')\np.write_text(p.read_text()+'x' if p.exists() else 'x')\n"
        f"print({output!r})\nraise SystemExit({code})\n", encoding='utf-8')
    ledger = tmp_path / '.showwork'
    ledger.mkdir()
    records = [
        {'session': 'genesis', 'claim': 'suite', 'check': {'type': 'command',
         'argv': ['python', 'scripts/run_tests.py'], 'stdout_contains': 'passed'}},
        {'session': 'genesis', 'claim': 'readme', 'check': {'type': 'file_exists', 'path': 'README.md'}},
    ]
    path = ledger / 'claims-2026-09-28.jsonl'
    path.write_text(''.join(json.dumps(r)+'\n' for r in records), encoding='utf-8')
    if not missing_readme:
        (tmp_path / 'README.md').write_text('exit gate', encoding='utf-8')
    return path, records


@pytest.mark.parametrize('code,output,missing,expected', [(0,'passed',False,0), (1,'passed',False,2), (0,'nothing',False,2), (0,'passed',True,2)])
def test_real_genesis_checks_run_once_and_propagate_failure(tmp_path, code, output, missing, expected):
    # REGRESSION: replacing a standalone suite must preserve command and artifact failures.
    fixture(tmp_path, code=code, output=output, missing_readme=missing)
    assert load_driver().run(tmp_path) == expected
    assert (tmp_path / 'calls').read_text() == 'x'


@pytest.mark.parametrize('mutation', ['missing', 'retracted', 'inline', 'duplicate', 'changed', 'weakened'])
def test_missing_or_changed_suite_refuses_before_execution(tmp_path, mutation):
    path, records = fixture(tmp_path)
    if mutation == 'missing': records.pop(0)
    elif mutation == 'retracted': records.append({'session':'genesis','retracted':True,'retracts':{'session':'genesis','claim':'suite'}})
    elif mutation == 'inline': records[0]['retracted'] = True
    elif mutation == 'duplicate': records.append({**records[0], 'claim':'second suite'})
    elif mutation == 'changed': records[0]['check']['argv'].append('--subset')
    elif mutation == 'weakened': records[0]['check']['expect_exit'] = 1
    path.write_text(''.join(json.dumps(r)+'\n' for r in records), encoding='utf-8')
    assert load_driver().run(tmp_path) == 2
    assert not (tmp_path / 'calls').exists()


def test_ci_has_one_genesis_entry_point():
    workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'run: .venv/bin/python scripts/check_ci_genesis.py' in workflow
    # REGRESSION: the verifier's 120-second default cut short a passing full suite.
    genesis_step = workflow.split('- name: Run the full behavioral suite through the genesis receipt')[1].split('\n      - name:')[0]
    assert 'SHOWWORK_COMMAND_TIMEOUT_SECONDS: "600"' in genesis_step
    assert 'run: .venv/bin/python scripts/run_tests.py' not in workflow
    assert 'run: .venv/bin/showwork verify --session genesis' not in workflow
