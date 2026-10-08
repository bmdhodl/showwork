"""Known defect: save returns without persisting the requested value."""


def save(path, value):
    pass


def load(path):
    return path.read_text(encoding="utf-8") if path.exists() else None
