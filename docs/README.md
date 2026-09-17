# showwork documentation

Start with the [README](../README.md). It demonstrates a failed close and
recovery in an empty directory.

## Learn by running it

- [Python quickstart](quickstart-python.md): an example that works across shells.
- [Cursor walkthrough](walks/cursor.md): integrate receipts into a coding session.
- [Claude Code adapter](claude-code.md): hook setup and its limits.

## Complete a task

- [Gate CI on receipts](ci.md)
- [Wrap agent commands](adapters.md)
- [Keep concurrent writers separate](concurrency.md)
- [Adopt showwork across repositories](fleet-adoption.md)
- [Migrate damaged legacy ledgers](legacy-baseline.md)

## Look up the contract

- [Ledger specification](../SPEC.md): records, check shapes, integrity, and lifecycle.
- [Source metadata](../pyproject.toml): branch version and Python support.
- [Public Python API](../src/showwork/__init__.py)
- [Changelog](../CHANGELOG.md)
- Run `showwork --help` and `showwork <command> --help` for your installed CLI.

## Understand the evidence

- [Evidence scope and failure case](evidence-scope.md)
- [Case study](case-study.md)
- [False Done Rate method](false-done-rate.md)
- [Evidence packs and their limits](compliance.md)

## Keep documentation current

Change the guide with the feature. Link to the specification and package
metadata instead of repeating versions and defaults. Keep historical
measurements dated and separate from installation instructions.

CI executes the README quickstart and checks local links through
`tests/test_documentation.py`. It also runs the existing quickstart,
packaging, and specification tests. See [CONTRIBUTING.md](../CONTRIBUTING.md)
for the full suite and receipt requirements.
