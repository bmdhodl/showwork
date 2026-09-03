"""Rendered Home/Activity badges: empty is unknown; click shows the claim."""

from __future__ import annotations

from pathlib import Path

from showwork.cli import main
from showwork.receipts import decorate_records, render_badges_html


def _run(root: Path, *argv: str) -> int:
    return main(["--root", str(root), *argv])


def _fixture_records(tmp_path: Path) -> list[dict]:
    (tmp_path / "ok.txt").write_text("ok", encoding="utf-8")
    assert _run(tmp_path, "start", "--session", "bmd-green") == 0
    assert _run(
        tmp_path, "claim", "--session", "bmd-green",
        "--claim", "ok.txt exists", "--type", "file_exists", "--path", "ok.txt",
    ) == 0
    assert _run(tmp_path, "start", "--session", "bmd-claimed") == 0
    assert _run(tmp_path, "claim", "--session", "bmd-claimed", "--claim", "said done") == 0
    rows = [
        {"task_id": "green", "title": "green run", "surface": "home"},
        {"task_id": "claimed", "title": "claimed run", "surface": "activity"},
        {"task_id": "missing", "title": "empty run", "surface": "home"},
    ]
    return decorate_records(rows, tmp_path)


def test_html_empty_workspace_is_unknown_not_verified(tmp_path):
    html = render_badges_html([], title="Home")
    assert 'data-state="unknown"' in html
    assert ">VERIFIED</summary>" not in html
    assert "No receipts yet." in html
    assert 'data-surface="home"' in html
    assert 'data-surface="activity"' in html


def test_html_green_and_claimed_render(tmp_path):
    records = _fixture_records(tmp_path)
    html = render_badges_html(records, title="Receipts")
    path = tmp_path / "home-activity.html"
    path.write_text(html, encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    assert 'data-state="verified"' in text
    assert 'data-state="claimed"' in text
    assert 'data-state="unknown"' in text
    assert "ok.txt exists" in text
    assert ">VERIFIED</summary>" in text
    assert ">CLAIMED</summary>" in text
    assert ">UNKNOWN</summary>" in text


def test_badge_markup_opens_claim_without_js(tmp_path):
    records = _fixture_records(tmp_path)
    html = render_badges_html(records)
    # <details> is the click surface. The claim is in the panel even when closed.
    assert "<details class=\"evidence\"" in html
    assert "<summary class=\"badge verified\"" in html
    assert "<p class=\"claim\">ok.txt exists</p>" in html
