"""Replay every historical check against today's tree, without rewriting receipts.

This is not reconstruction of historical environments or certification of every
session outcome. It evaluates claim checks and immutable acceptance requirements.
The independent chain audit still owns ledger-integrity findings.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from showwork.checks import EXIT_BY_VERDICT, evaluate_records, verify_claim
from showwork.ledger import iter_ledger_jsonl, load_all_claims, load_all_events
from showwork.outcomes import evaluate_requirement_records


def ledger_manifest(root):
    manifest = {}
    for path in iter_ledger_jsonl(root):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Ledger path escapes the replay checkout')
        manifest[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def replay(root):
    root = root.resolve()
    before = ledger_manifest(root)
    claims, events = load_all_claims(root), load_all_events(root)
    cache = {}  # One invocation only; no persistent or cross-revision green cache.
    state = evaluate_records(claims, root, label='all historical claims',
                             command_cache=cache)
    requirements = [row for row in events if row.get('event') == 'session.requirement']
    rows = state['results'] + evaluate_requirement_records(root, requirements,
                                                          command_cache=cache)
    rows += [verify_claim(row, root) for row in events if row.get('_parse_error')]
    if ledger_manifest(root) != before:
        rows.append({'claim': 'replay preserves historical ledger bytes', 'session': '',
                     'type': 'ledger-preservation', 'severity': 'RED', 'status': 'fail',
                     'detail': 'ledger files changed during replay; results cannot certify unchanged history'})
    failed = [row for row in rows if row['status'] in {'fail', 'error'}]
    active = [row for row in rows if not row.get('retracted')]
    if any(row['status'] == 'fail' and row['severity'] == 'RED' for row in failed):
        verdict = 'RED'
    elif failed or not active or any(row['status'] == 'skipped' for row in active):
        verdict = 'YELLOW'
    else:
        verdict = 'GREEN'
    return {
        'scope': 'historical checks replayed against current tree; not historical outcome certification',
        'verdict': verdict, 'total': len(active),
        'passed': sum(row['status'] == 'pass' for row in active),
        'requirement_count': len(requirements), 'results': rows,
        'limitations': ['integrity is audited separately',
                        'missing check specs remain unverified',
                        'shared suite evidence uses the bounded source snapshot'],
    }


def main():
    state = replay(ROOT)
    print(json.dumps(state, indent=2))
    return EXIT_BY_VERDICT[state['verdict']]


if __name__ == '__main__':
    raise SystemExit(main())
