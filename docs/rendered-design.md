# BMD rendered design

`DESIGN.md` v1.2.0 is the shared authority. `design-tokens.css` and
`design-tokens.json` are its generated exports. The approved loop tile is
`bmd-loop-mark-512.png`; tests pin its canonical SHA-256.

`design-surfaces.css` adapts the shared tokens to this product. Run
`python scripts/sync_design_assets.py` after an export or presentation change.
The generated Python module embeds CSS and the raster mark so standalone HTML
works offline and installed packages need no asset server or runtime dependency.
The module, generated tokens, and served copies are checked for drift.

## Acceptance

- `python scripts/check_rendered_design.py` exercises real renderer output and
  rejects missing or altered branding. These regressions failed before the fix.
- `npm run test:e2e` uses the dev-only Python Playwright dependency to render
  maintained surfaces at 375, 768 and 1440. It checks logo loading, boundaries,
  readable type, text contrast, keyboard entry, reduced motion, overflow and
  200% CSS zoom. Screenshots and reading counts go to `output/playwright/`.
- Automated checks do not certify comprehension. A reviewer must still identify
  purpose, state and next action. Root-task visual review is separate evidence.
- Historical screenshots, release videos and exported reports remain historical.
  Regeneration uses the new design. This PR does not publish or deploy a product.

## Maintained sources

`src/showwork/dashboard.py` renders replay summaries, including empty and
intervention states. `src/showwork/receipts.py` renders verified, claimed, failed
and unknown receipts. Status labels, scope warnings, integrity details and
recovery text remain intact. Native `details` disclosure works with keyboard
Enter. Reports retain their factual limits; a new style cannot change a verdict.
The existing `scripts/check_receipts_ui.py` remains a separate acceptance gate.
