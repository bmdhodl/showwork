# Test source-checkout isolation — r27

Date: 2026-08-15  
Scope: test harness only; no runtime package behavior, API, schema, release,
public copy, or dependency change.  
Session: `test-source-isolation-r27-20260815`

## Finding

Before this change, `python -c "import showwork"` from `K:\showwork` resolved
to the unrelated editable clone at
`<showwork-checkout>\src\showwork\__init__.py`, even
though `pyproject.toml` declared `pythonpath = ["src"]`. The existing test
gate therefore depended on interpreter-installed path ordering and could test
the wrong checkout. This was the same harness distinction found during the
r27 checker readout.

## Change

`tests/conftest.py` now removes and prepends this checkout's `src` directory
before test collection. `tests/test_source_checkout.py` asserts that the
imported `showwork.__file__` resolves to `K:\showwork\src\showwork`.

This fixes pytest's source selection only. It does not claim that arbitrary
standalone Python processes or editable installs select K:\showwork without an
explicit environment or reinstall; those remain operator-environment facts.

## Evidence

- Before the guard, default import path: `<showwork-checkout>\src\showwork`.
- After the guard, the regression test passed and asserted the K checkout path.
- Focused behavior gate: `python -m pytest tests/test_checks.py tests/test_source_checkout.py -q` -> `66 passed`.
- Default full gate after the guard: `python -m pytest tests/ -q` -> `242 passed`.

The full gate now collects and verifies the K checkout through the regression
test; it no longer silently accepts the unrelated editable clone as the
package under test.

The test-only guard is compatible with the existing `src` package layout and
does not alter production imports once the package is installed or built.

## Boundary and remaining gap

No runtime source, checker, schema, receipt, adapter, release, or public copy
changed. The environment still contains an unrelated editable install, so
release/CLI validation should continue to use the intended checkout or an
isolated virtual environment. This report does not establish package adoption,
registry state, or cross-environment behavior.
