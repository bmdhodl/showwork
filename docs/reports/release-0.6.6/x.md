---
title: showwork 0.6.6
excerpt: Merging main no longer fails your agent's check.
---

I merged main into my agent's branch. The showwork check went red over README.md.

The agent never touched it. A teammate did, on main.

0.6.6 compares the file with main. Same bytes: green. Agent edits it in the merge: still red.

pip install -U showwork
