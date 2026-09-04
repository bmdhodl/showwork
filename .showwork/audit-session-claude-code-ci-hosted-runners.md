# Claims audit - session claude-code-ci-hosted-runners

**Verdict: GREEN**  (8/8 verified)

- OK **The Python test job runs on GitHub-hosted runners, not the shared box** (`file_contains`)
    - /test:\n    if:.*\n    runs-on: ubuntu-latest/ found in .github/workflows/ci.yml
- OK **The clean-room matrix, five jobs per PR, runs on GitHub-hosted runners** (`file_contains`)
    - /runs-on: ubuntu-latest/ found in .github/workflows/clean-room-action.yml
- OK **conformance-js still uses host-provisioned Node, so the no-setup-node policy holds** (`file_contains`)
    - /Require host-provisioned Node.js 24/ found in .github/workflows/ci.yml
- OK **No setup-node action was introduced into ci.yml** (`file_contains`)
    - /actions/setup-node@/ absent as claimed
- OK **publish.yml stays self-hosted because it calls ci-heavy-slot on that box** (`file_contains`)
    - /runs-on: \[self-hosted, linux, x64, pc\]/ found in .github/workflows/publish.yml
- OK **Publishing never cancels in progress, so a PyPI upload cannot be interrupted** (`file_contains`)
    - /cancel-in-progress: false/ found in .github/workflows/publish.yml
- OK **CI supersedes its own stale pull-request runs instead of holding a runner** (`file_contains`)
    - /concurrency:/ found in .github/workflows/ci.yml
- OK **The full suite passes with these workflow changes in place** (`command`)
    - exit 0, stdout has 'passed'
