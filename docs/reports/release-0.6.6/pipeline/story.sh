#!/usr/bin/env bash
# Release story: a PR merges main to stay up to date, then the receipt gate runs.
# Usage: story.sh <venv-dir> <work-dir> [touch-shared]
# With touch-shared, the session also edits README.md inside the merge.
set -u
VENV="$1"; WORK="$2"; MODE="${3:-clean}"
SW() { "$VENV/Scripts/python" -m showwork --root "$WORK" "$@"; }
rm -rf "$WORK"; mkdir -p "$WORK"; cd "$WORK"
git init -q; git config user.name demo; git config user.email demo@example.invalid
git config core.autocrlf false
printf 'print("tests passed")\n' > check.py
printf 'Login guide, draft one.\n' > README.md
git add -A; git commit -q -m base; git branch -M main
git checkout -q -b fix-login

echo "## agent session on fix-login"
SW start --session fix-login >/dev/null
SW require --session fix-login --id suite --description "check.py passes" \
  --scope behavior --type command --command-arg python --command-arg check.py >/dev/null
printf 'def login():\n    return True\n' > login.py
SW claim --session fix-login --claim "login.py exists" --type file_exists --path login.py >/dev/null
SW finish --session fix-login | head -1
git add -A; git commit -q -m "fix login, with receipt"

echo "## a teammate's PR lands on main"
git checkout -q main
printf 'Login guide, reviewed.\n' > README.md
git commit -q -am "teammate edits the README"
BASE=$(git rev-parse main)
git checkout -q fix-login

echo "## branch protection: merge main into fix-login"
if [ "$MODE" = "touch-shared" ]; then
  # The agent edits README.md before it commits the merge, so the edit is
  # part of the merge commit itself.
  git merge -q --no-commit --no-ff main
  printf 'Login guide, edited by the agent.\n' > README.md
  git add README.md
  git commit -q --no-edit
  echo "(the merge commit also changed README.md to Login guide, edited by the agent.)"
else
  git merge -q --no-edit main
fi

echo "## CI receipt job: gate --changed-since <PR base SHA>"
SW gate --changed-since "$BASE" --require-tracked
echo "exit=$?"
