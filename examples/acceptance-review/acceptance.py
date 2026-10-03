"""A tiny persistence application and acceptance probe with explicit mutations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


class SettingsStore:
    """Persist string settings, including across a new instance/process."""

    def __init__(self, root: Path):
        self.path = root / "settings.json"

    def read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in data.items()):
            raise ValueError("settings must map strings to strings")
        return data

    def get(self, key: str) -> str | None:
        return self.read().get(key)

    def put(self, key: str, value: str) -> None:
        if not isinstance(key, str) or not key or not isinstance(value, str):
            raise ValueError("a nonempty string key and string value are required")
        data = self.read()
        data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        pending = self.path.with_suffix(".tmp")
        pending.write_text(json.dumps(data) + "\n", encoding="utf-8")
        pending.replace(self.path)


class EmptyStore(SettingsStore):
    """Mutation: production write is removed; fixture must not replace it."""

    def put(self, key: str, value: str) -> None:
        pass


class CacheOnlyStore(SettingsStore):
    """Mutation: same-instance read works but nothing survives reopen."""

    def __init__(self, root: Path):
        self.cache = {}

    def read(self) -> dict[str, str]:
        return dict(self.cache)

    def put(self, key: str, value: str) -> None:
        self.cache[key] = value


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise AssertionError(reason)


def accept_store(factory, root: Path) -> None:
    """Fixtures supply only inputs. Every persisted output comes from put."""
    store = factory(root)
    require(store.get("theme") is None, "test needs a fresh, empty store")
    store.put("theme", "dark")
    require(store.get("theme") == "dark", "write/read behavior is missing")
    reopened = factory(root)
    require(reopened.get("theme") == "dark", "value did not survive reopen")
    reopened.put("contrast", "high")
    require(factory(root).read() == {"theme": "dark", "contrast": "high"}, "reopened update lost data")


def read_existing(root: Path) -> None:
    """A fresh process may read evidence; it never seeds a missing output."""
    require(SettingsStore(root).read() == {"theme": "dark", "contrast": "high"}, "persisted output missing or incorrect")
    print("persisted values read")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--mutation", choices=["empty-write", "cache-only"])
    parser.add_argument("--read-existing", action="store_true")
    args = parser.parse_args()
    try:
        if args.read_existing:
            read_existing(args.root)
        else:
            factory = {"empty-write": EmptyStore, "cache-only": CacheOnlyStore}.get(args.mutation, SettingsStore)
            accept_store(factory, args.root)
            print("write/read/reopen acceptance passed")
    except (AssertionError, OSError, ValueError) as exc:
        print(f"acceptance failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
