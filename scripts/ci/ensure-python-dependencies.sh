#!/usr/bin/env bash
set -euo pipefail

exec 9>"${TMPDIR:-/tmp}/showwork-dependencies.lock"
flock 9

force=false
if [[ "${1:-}" == "--force" ]]; then
  force=true
elif [[ $# -gt 0 ]]; then
  printf 'Usage: %s [--force]\n' "${0##*/}" >&2
  exit 64
fi

venv_dir="${CI_VENV_DIR:-.venv}"
marker="$venv_dir/.ci-dependencies.sha256"
dependency_hash="$({
  sha256sum pyproject.toml
  python3 --version
} | sha256sum | awk '{print $1}')"

if [[ "$force" == false && -x "$venv_dir/bin/python" && -f "$marker" && "$(cat "$marker")" == "$dependency_hash" ]]; then
  printf 'Dependencies unchanged. Reusing %s.\n' "$venv_dir"
  exit 0
fi

printf 'Dependency inputs changed. Rebuilding %s.\n' "$venv_dir"
rm -rf -- "$venv_dir"
python3 -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --prefer-binary --cache-dir "${PIP_CACHE_DIR:-$HOME/.cache/pip}" --upgrade pip build pytest
"$venv_dir/bin/python" -m pip install --prefer-binary --cache-dir "${PIP_CACHE_DIR:-$HOME/.cache/pip}" -e .
printf '%s\n' "$dependency_hash" > "$marker"
