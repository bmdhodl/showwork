# showwork PowerShell onboarding command audit r12

Date: 2026-08-15  
Scope: one clean disposable Windows PowerShell proof root using the public
PyPI package and a synthetic local marker. No README, package, script, schema,
public-copy, traffic, adoption, compliance, authority, reproducibility, or
release claim.

## Result

The installed public package completed the minimal local proof in PowerShell:
`showwork 0.3.0`, one claim GREEN, audit GREEN, and finish GREEN. Running the
documented evidence-pack path from the proof root failed because the script is
not present there. Re-running it with an explicit checkout path succeeded. The
observed recommendation is a future release-gate fixture, not a public-copy
change in this task.

Decision: **KEEP** the current product surface and refusal language.

## Environment

- Windows 11 build `10.0.26200`.
- Python `3.13.2` from `C:\Python313\python.exe`.
- Clean proof root: `<temp>\showwork-powershell-r12-20260815-clean`.
- Venv creation: exit 0, 4,300.4 ms.
- `pip install showwork`: exit 0, 1,389.0 ms, installed `0.3.0`.
- Input: `marker.txt` containing synthetic local text.

## Exact command transcript

| command phase | exit | elapsed | observed result |
|---|---:|---:|---|
| venv creation | 0 | 4,300.4 ms | clean venv |
| `pip install showwork` | 0 | 1,389.0 ms | installed `showwork 0.3.0` |
| `showwork start --session powershell-r12 --agent codex` | 0 | 119.0 ms | session started |
| `showwork claim ... --type file_exists --path marker.txt` | 0 | 81.2 ms | claim recorded |
| `showwork verify --date 2026-08-15 --no-report` | 0 | 87.3 ms | GREEN, 1/1 verified |
| `showwork audit` | 0 | 93.3 ms | GREEN, 2/2 records chained |
| `showwork finish --session powershell-r12 --status ok` | 0 | 86.7 ms | GREEN, 1/1 verified |
| `python scripts/evidence_pack.py ...` from proof root | 2 | 56.8 ms | file absent in proof root |
| `python K:\showwork\scripts\evidence_pack.py ...` | 0 | 107.0 ms | pack written from explicit checkout |

The failed evidence-pack command is a bounded path/documentation friction
observation. It is not a package failure or a claim that every PowerShell
reader will encounter the same timing.

## Future fixture

At a future owner-approved release, run this transcript in a clean PowerShell
root and assert that the installed version is recorded, the minimal predicate
closes GREEN, `audit` is 2/2 for the one-claim proof, and the evidence-pack
command uses an explicit checkout path when the script is not packaged. Keep
the command path and recovery visible in the fixture output.

