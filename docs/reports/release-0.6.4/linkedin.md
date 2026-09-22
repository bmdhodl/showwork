---
title: showwork 0.6.4
excerpt: The close was refused because add(2, 2) returned 5.
---

add(2, 2) returned 5. The test expected 4. The agent still called the task done.

showwork 0.6.4 refused that close. Exit code 2. Two file checks passed. The behavior check failed.

The repair was one line: return a + b. The same check then passed 3 of 3.

A receipt now shows the requirement, the check, the result, and the old finish. Text and JSON match. A second process can read the receipt. That read does not run the command, and it does not inherit the close.

The pilot count is still 0 activations and 0 repeat users.

pip install showwork
