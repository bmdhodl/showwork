---
title: showwork 0.6.6
excerpt: Merging main no longer fails your agent's check.
---

I merged main into my agent's branch, and showwork failed the agent for a file it never touched.

My test is a short script in a clean repo. An agent session fixes login on a branch, and both of its checks pass. A teammate edits README.md on main. The repo wants branches up to date, so the branch merges main. Then CI runs the showwork check.

showwork 0.6.5 said RED: undeclared change, README.md. It counted the teammate's edit against the agent.

showwork 0.6.6 compares the file with main first. The branch copy and the main copy had the same bytes, so the change came from main. The check passed and listed README.md in a note.

The check did not get softer. In a second run the agent edited README.md during the merge. The file no longer matched main, and 0.6.6 still said RED.

Both versions came from PyPI and ran the same script.

If your CI runs the showwork check on branches that merge main, upgrade. GitHub Action users: pin v0.6.6.

pip install -U showwork

github.com/bmdhodl/showwork
