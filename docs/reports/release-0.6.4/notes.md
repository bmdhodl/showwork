---
title: showwork 0.6.4
excerpt: add(2, 2) returned 5. finish refused the close.
---

showwork 0.6.4 is on PyPI.

add(2, 2) returned 5. The test expected 4. finish exited 2 and refused the close. The repair returned a + b. The same check then passed 3 of 3.

require and claim now reject a bad flag before they write a record. --absent is valid on file_contains only.

A receipt shows the requirement, the check, the result, and the old finish. The text and the JSON match. A bad receipt stays unverified.

A second process can read that receipt. It does not run the recorded command. It does not inherit the close.

The opt-in pilot count is 0 activations and 0 repeat users.

pip install showwork
