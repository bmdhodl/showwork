"""Reproduce the GolfFly verification gap without downloading the game."""

import json
import os
import tempfile
from pathlib import Path

from showwork.ledger import finish_session, record_claim, start_session, verify_session
from showwork.outcomes import record_requirement


def main():
    # This bounded demo verifies only its temporary leaf fixtures, never the
    # enclosing repository. Allow it to run as an acceptance command itself.
    os.environ.pop("SHOWWORK_VERIFYING", None)
    with tempfile.TemporaryDirectory(prefix="showwork-evidence-demo-") as folder:
        root = Path(folder)
        (root / "controller.py").write_text('# m.weights\ndef shot(model): return 10\n')
        (root / "check.py").write_text(
            'from controller import shot\nassert shot(3) == 3\nprint("shot preserved")\n')
        (root / "receipt.json").write_text('{"invented_test_count":2360}')
        start_session(root, "strings")
        for path, pattern in [("controller.py", "m.weights"), ("receipt.json", "2360")]:
            record_claim(root, "strings", "The model controls the shot and tests passed",
                         {"type": "file_contains", "path": path, "pattern": pattern})
        state = verify_session(root, "strings")
        code, _ = finish_session(root, "strings")
        assert state["passed"] == 2 and code == 2
        print("Strings match: 2 checks pass. Outcome unverified. Close refused.")
        start_session(root, "behavior")
        record_requirement(root, "behavior", "shot", "Controller preserves the model's shot",
                           "behavior", {"type": "command", "argv": ["python", "check.py"]})
        record_claim(root, "behavior", "controller.py is present",
                     {"type": "file_exists", "path": "controller.py"})
        assert finish_session(root, "behavior")[0] == 2
        print("Controller overwrites the shot: acceptance test fails. Close refused.")
        (root / "controller.py").write_text('def shot(model): return model\n')
        code, state = finish_session(root, "behavior")
        assert code == 0
        print("Controller preserves the shot: acceptance test passes. Close accepted.")
        print(json.dumps(state["outcome"]))


if __name__ == "__main__":
    main()
