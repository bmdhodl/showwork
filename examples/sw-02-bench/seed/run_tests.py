import sys

import pytest

code = pytest.main(["-q", "test_add.py"])
if int(code) == 0:
    print("passed")
sys.exit(int(code))
