"""The test gate imports the package from the checkout under test."""

from pathlib import Path

import showwork


def test_showwork_import_is_current_checkout():
    expected = (Path(__file__).resolve().parents[1] / "src" / "showwork").resolve()
    actual = Path(showwork.__file__).resolve().parent
    assert actual == expected
