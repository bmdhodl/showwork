# examples/

Runnable copies live in the installed package, not only in this folder.

    pip install showwork
    python -m showwork init

That writes:

- `.cursor/rules/showwork.mdc`
- `.claude/settings.json` Stop hook (merged if the file exists)
- `docs/ci/showwork-verify.yml` (copy into `.github/workflows/` yourself)

The empty-directory refusal walk is the README Quickstart. The Cursor walk is docs/walks/cursor.md. The older prompt contract is docs/examples/agent-prompt.md.

BMD desktop (read-only supervisor) is examples/bmd/. The sidecar reads
`.showwork/` in the user workspace and never appends.
