from pathlib import Path

from add import add


def test_add():
    assert add(2, 2) == 4


def test_config():
    text = Path("config.txt").read_text(encoding="utf-8")
    assert "timeout: 30" in text
