"""Run the full behavioral suite once, through its existing genesis claim.

This is repository CI plumbing, not a new verifier or a cached green result.
The genesis command must remain the complete test entry point. All its other
claims still run, and malformed or changed requirements fail closed.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from showwork.checks import EXIT_BY_VERDICT, apply_append_retractions, render_report
from showwork.ledger import claims_for_session, verify_session
from showwork.outcomes import requirement_records


def run(root: Path) -> int:
    records = apply_append_retractions(claims_for_session(root, 'genesis'))
    active = [record for record in records if not record.get('retracted')
              and not record.get('_append_retraction_reason')]
    commands = [record.get('check') for record in active
                if isinstance(record.get('check'), dict)
                and record['check'].get('type') == 'command']
    expected = {'type': 'command', 'argv': ['python', 'scripts/run_tests.py'],
                'stdout_contains': 'passed'}
    if (len(commands) != 1
            or {k: v for k, v in commands[0].items() if k != 'expect_exit'} != expected
            or type(commands[0].get('expect_exit', 0)) is not int
            or commands[0].get('expect_exit', 0) != 0
            or requirement_records(root, 'genesis')):
        print('REFUSED: genesis must retain exactly one unchanged full-suite command and no additional requirements')
        return 2
    state = verify_session(root, 'genesis')
    print(render_report(state))
    return EXIT_BY_VERDICT[state['verdict']]


if __name__ == '__main__':
    raise SystemExit(run(ROOT))
