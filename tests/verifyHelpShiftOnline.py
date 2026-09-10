#!/usr/bin/env python3
"""Online half of verifyHelpShift — last in run_all, after the offline suite.

Brings the device onto the network and asserts Contact Us opens PeopleFun
Support. The offline redirect stays in tests/verifyHelpShift.py (after Options).

    ./.venv/bin/python tests/verifyHelpShiftOnline.py
    ./.venv/bin/python tests/verifyHelpShift.py --online
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.verifyHelpShift import run_online as run  # noqa: E402


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
