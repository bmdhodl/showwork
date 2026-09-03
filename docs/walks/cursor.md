# Cursor walk: first refused false done

This is the ten-minute path on a repo you already have. Commands are one line
so they paste in PowerShell and in bash.

## 1. Install

```bash
pip install showwork
python -m showwork --help
```

`python -m showwork` is the same program as the `showwork` script.

## 2. Glue (optional, once per repo)

```bash
python -m showwork init --cursor
```

That writes `.cursor/rules/showwork.mdc`. Restart the agent chat so the rule
loads. Set `SHOWWORK_SESSION=cursor-first-look` in the terminal you give the
agent.

## 3. See a refusal in an empty folder

From a new empty directory, not your real repo:

```bash
python -m showwork start --session first-look --agent cursor
python -m showwork claim --session first-look --claim "config/api.yaml exists" --type file_exists --path config/api.yaml
python -m showwork finish --session first-look --status ok
```

Exit code 2. Stderr contains `REFUSED`. The file was never written. That is
the product.

## 4. Recover

```bash
python -c "from pathlib import Path; p=Path('config'); p.mkdir(exist_ok=True); (p/'api.yaml').write_text('timeout: 30\n')"
python -m showwork retract --session first-look --claim "config/api.yaml exists" --reason "file was not written yet"
python -m showwork claim --session first-look --claim "config/api.yaml exists" --type file_exists --path config/api.yaml
python -m showwork finish --session first-look --status ok
```

Exit code 0. Commit `.showwork/` with the work.

## 5. On your real repo

Start a session, let the Cursor rule drive claims after each change, and
close with `finish --status ok`. If you delete a file you did not claim,
verify goes RED. That is issue #64.

CI: copy `docs/ci/showwork-verify.yml` (written by `showwork init --ci`) into
`.github/workflows/`. Pin `bmdhodl/showwork/actions/verify` to a release tag.
Until 0.4.0 is on PyPI, the action still installs from the action ref, so a
tag or SHA is enough.
