"""Exercise the rendered receipt states with Chromium, not HTML string checks."""

import argparse
import json
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from showwork.ledger import finish_session, record_claim, record_supersession, start_session
from showwork.outcomes import record_requirement
from showwork.receipts import decorate_records, render_badges_html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="showwork-browser-") as folder:
        root = Path(folder)
        (root / "receipt.txt").write_text("2360")
        start_session(root, "loose")
        record_claim(root, "loose", "All tests and HDR passed",
                     {"type": "file_exists", "path": "receipt.txt"})
        start_session(root, "artifact")
        record_requirement(root, "artifact", "file", "receipt.txt exists", "artifact",
                           {"type": "file_exists", "path": "receipt.txt"})
        record_claim(root, "artifact", "receipt.txt exists",
                     {"type": "file_exists", "path": "receipt.txt"})
        assert finish_session(root, "artifact")[1]["outcome"]["verdict"] == "VERIFIED"
        note_claim = "one plan note matches notes/v1-*.md"
        start_session(root, "earlier")
        record_requirement(root, "earlier", "file", "receipt.txt exists", "artifact",
                           {"type": "file_exists", "path": "receipt.txt"})
        (root / "notes").mkdir()
        (root / "notes" / "v1-plan.md").write_text("plan")
        record_claim(root, "earlier", note_claim,
                     {"type": "glob_count", "pattern": "notes/v1-*.md", "op": "==", "n": 1})
        assert finish_session(root, "earlier")[1]["outcome"]["verdict"] == "VERIFIED"
        start_session(root, "later")
        (root / "notes" / "v1-plan.md").rename(root / "notes" / "v2-plan.md")
        record_claim(root, "later", "the plan note moved to v2",
                     {"type": "path_moved", "from": "notes/v1-plan.md", "to": "notes/v2-plan.md"})
        record_supersession(root, "later", "earlier", note_claim,
                            "the v2 release renames the plan note")
        rows = decorate_records([
            {"session": "loose", "title": "Unproven behavior", "surface": "home"},
            {"session": "artifact", "title": "Declared file check", "surface": "activity"},
            {"session": "earlier", "title": "Superseded claim", "surface": "activity"},
        ], root)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for width in (375, 768, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                page.set_content(render_badges_html(rows))
                claimed = page.locator('article[data-state="claimed"]')
                assert claimed.count() == 1
                assert not claimed.locator(".panel").is_visible()
                claimed.locator("summary").click()
                assert claimed.locator(".panel").is_visible()
                assert "outcome requirements are unverified" in claimed.inner_text()
                verified = page.locator('details[data-session="artifact"]')
                assert verified.get_attribute("data-state") == "verified"
                verified.locator("summary").click()
                assert "0 behavior, 1 artifact" in verified.inner_text()
                assert "Unlisted requirements: unknown" in verified.inner_text()
                superseded = page.locator('details[data-session="earlier"]')
                assert superseded.get_attribute("data-state") == "verified"
                assert not superseded.locator(".superseded").is_visible()
                superseded.locator("summary").click()
                assert superseded.locator(".superseded").is_visible()
                assert ("superseded by session later: the v2 release renames the plan note"
                        in superseded.locator(".superseded").inner_text())
                assert page.evaluate("document.documentElement.scrollWidth") == width
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(args.screenshot), full_page=True)
            page.set_content(render_badges_html([]))
            assert page.get_by_text("UNKNOWN", exact=True).is_visible()
            page.get_by_text("UNKNOWN", exact=True).click()
            assert page.get_by_text("No receipts yet.").is_visible()
            assert page.locator('article[data-state="verified"]').count() == 0
            assert not errors, errors
            browser.close()
    print(json.dumps({"passed": True, "viewports": [375, 768, 1440],
                      "checks": ["loose claim stays claimed", "artifact scope visible",
                                 "superseded claim names its session", "details open",
                                 "no overflow", "empty state unknown", "no page errors"]}))


if __name__ == "__main__":
    main()
