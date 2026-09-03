"""Allow `python -m showwork` after a plain pip install."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
