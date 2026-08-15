# showwork process-tree timeout design readout r17

Date: 2026-08-15  
Scope: design comparison only, grounded in the r16 disposable timeout report
and current `src/showwork/cli.py`. No live process was killed in this readout;
no wrapper/runtime/schema/workflow/release change was made.

## Current boundary

The wrapper uses `subprocess.run(..., timeout=...)`. The r16 fixture showed a
timed-out parent returned a durable `budget_exceeded` receipt while an owned
detached descendant remained alive immediately after wrapper return. A partial
claims receipt remained visible. A parent that exited independently could return
success while its child was still alive. This is not hard real-time or process
tree termination proof.

## Platform design matrix

| option | strength | failure/ownership boundary | design status |
|---|---|---|---|
| direct `Popen.kill` | simple direct-child cleanup | descendants and detached children survive | current helper behavior; insufficient for tree semantics |
| POSIX `start_new_session` + process-group signal | gives the wrapper an owned session and permits `killpg`; hard-kill fallback is possible | child can call `setsid`/daemonize, signals can be handled/ignored, orphan/reap behavior needs tests | candidate; no implementation chosen |
| Windows new process group + `taskkill /PID /T` | bounded command can target the exact wrapper PID and its children | race if parent exits first, permissions/tool availability, breakaway children, forceful termination semantics | candidate fallback; no guarantee |
| Windows Job Object with kill-on-close | stronger explicit process membership and group termination | native API/handle lifecycle, nested-job and breakaway rules, permissions, zero-dependency portability cost | strongest design candidate; requires explicit owner decision |

Python documents `start_new_session` and Windows process-group creation flags;
Microsoft documents that Job Objects can associate groups of processes and
terminate a job, while `taskkill /T` terminates a selected process and its
children. These platform primitives describe options, not current showwork
behavior.

## Required future tests

Any implementation would need parent-only, child, grandchild, child that
ignores soft termination, parent-independent exit, partial receipt, cleanup
failure, process-group escape, and “unrelated sibling survives” cases on both
Windows and POSIX. Tests must assert wrapper exit/budget receipt, descendant
liveness after a bounded grace period, no unrelated process termination, and
temporary-file cleanup. They must not make a hard real-time or universal
daemon-kill claim.

## Decision

**OWNER-GATED DESIGN-ONLY / NO CHANGE.** Keep the existing wrapper and its
limits. Do not implement process-tree policy from this readout or claim that
showwork currently terminates descendants.

Validation: `python -m pytest tests/ -q --basetemp=...` -> **239 passed**.
