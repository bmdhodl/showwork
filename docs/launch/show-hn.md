# Show HN: showwork – agents have to prove the done (draft)

Do not submit until PyPI serves 0.4.0. Numbers below are from the repo and from the 2026-09-03 survey in the stranger prompt. None of them are invented.

Title: Show HN: showwork – a receipt that refuses a false agent done

Body:

Observability tools log what an agent did. showwork verifies what the agent claimed it did, against the files, and refuses `finish --status ok` when a claim is false (exit 2).

Stdlib Python. pip install showwork. Then:

    showwork start --session first-look --agent cursor
    showwork claim --session first-look --claim "config/api.yaml exists" --type file_exists --path config/api.yaml
    showwork finish --session first-look --status ok

That close is supposed to fail. The file does not exist. The refusal is the product.

Day-0 on the author's own agent fleet: 21 sessions, 42.9% contained a false done. Every one was caught by the gate. Method: docs/false-done-rate-day0.md in the repo.

Surveyed 2026-09-03, before this work: 0 GitHub stars, 1 fork, 448 lifetime PyPI downloads, one stranger issue. The package has existed on PyPI since July. I am the only user I can prove.

Repo: https://github.com/bmdhodl/showwork
Spec: spec-v0.4 in SPEC.md (append-only JSONL, hash chain, eight check types, plus undeclared-change against the start snapshot)

I will not bless a GREEN that CI never reads. The composite action is actions/verify. A drop-in workflow is docs/ci/verify.yml.
