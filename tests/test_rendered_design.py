"""REGRESSION: receipts and dashboards share the offline BMD identity."""
import pytest
from showwork.dashboard import render
from showwork.receipts import render_badges_html


@pytest.mark.parametrize('html', [render({}), render_badges_html([])], ids=['dashboard','receipts'])
def test_rendered_surfaces_share_tokens_and_offline_logo(html):
    assert 'class="bmd-mark"' in html
    assert 'data:image/png;base64,' in html
    assert '--bmd-colors-background: #0a0a0a;' in html
    assert 'font-size: 16px' in html

def test_generated_render_assets_match_source():
    import hashlib
    import runpy
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    generator = runpy.run_path(str(root / "scripts/sync_design_assets.py"))
    assert generator["TARGET"].read_text(encoding="utf-8") == generator["expected"]()
    assert hashlib.sha256((root / "bmd-loop-mark-512.png").read_bytes()).hexdigest() == "362d797dd2920fadda6ae91488143780ba6ca2951aefedda3d71061de3a3c1cc"
