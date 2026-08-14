#!/usr/bin/env bash
# Example: Agent finish workflow with showwork
#
# This script demonstrates the full lifecycle: start, claim, finish, and
# what to do when the gate refuses.

set -euo pipefail

session="deploy-api-timeout"

# Start the session
showwork start --session "$session" --agent claude-code

# The agent makes a change
echo "timeout: 30" > config/api.yaml

# Record a falsifiable claim
showwork claim --session "$session" \
  --claim "bumped the API timeout to 30 seconds" \
  --type file_contains \
  --path config/api.yaml \
  --pattern "timeout: 30"

# Run tests and record the outcome
if python scripts/run_tests.py; then
  showwork claim --session "$session" \
    --claim "tests pass" \
    --type command \
    --command-arg python \
    --command-arg scripts/run_tests.py
else
  echo "Tests failed. Blocking the finish."
  showwork finish --session "$session" --status blocked
  exit 1
fi

# Close through the exit gate
if showwork finish --session "$session" --status ok; then
  echo "Session closed cleanly. Claims verified."
  git add .showwork/
  git commit -m "feat: increase API timeout to 30 seconds"
else
  echo "ERROR: The exit gate refused. Claims are RED."
  echo "Fix the gap or retract the false claim, then finish again."
  exit 2
fi
