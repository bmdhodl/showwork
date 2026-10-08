"""Repair: save persists the value for a fresh reader."""


def save(path, value):
    path.write_text(value, encoding="utf-8")


def load(path):
    return path.read_text(encoding="utf-8") if path.exists() else None
