# Adopting showwork with damaged shared history

Version 0.6.0 correctly refused the website's release because three old shared
ledgers failed integrity checks. One old `prev` field held a Git commit ID;
later fields contained values that were not hashes of earlier records. Other
files mixed chained and unchained rows. Replacing those fields now would invent
historical evidence.

Version 0.6.1 provides an explicit, optional boundary for new work. An operator
reviews a full ancestor commit ID and pins its shared legacy files:

```bash
python -m showwork gate --session NEW_SESSION --require-tracked \
  --legacy-integrity-baseline FULL_REVIEWED_COMMIT_ID
```

The GitHub Action accepts the same `legacy-integrity-baseline` input. Supply an
actual 40- or 64-character commit ID, never `main`, `HEAD`, or a moving PR base.
Protect changes to this CI input through your repository's review policy.

The baseline predates the selected session. All its shared legacy files stay
present and identical in both HEAD and the working tree, with LF/CRLF checkout conversion allowed. Editing,
deleting, renaming or replacing one fails. New broken files fail. Per-session
receipts cannot be acknowledged this way, and the selected session cannot be
part of the pinned legacy history.

Restoring old bytes as an uncommitted file cannot hide a changed or missing
file in HEAD. The released commit must contain the pinned regular file too.

The gate output names the pinned commit, each acknowledged RED file, and its
audit failure. A passing current acceptance result does not change historical
integrity to GREEN. `showwork audit` still returns RED. The raw files and their
original Git history remain intact.

All commands run before the final integrity observation. A test that writes a
broken receipt therefore fails the gate even when its process returns zero.

This option trusts the operator's baseline choice. It is not proof of old
claims, independent approval, a sandbox, or permission to move the boundary
forward automatically. Strict refusal remains the default. If the requirement
is intact history for the entire repository, do not use this exception.
