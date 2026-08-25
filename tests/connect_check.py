#!/usr/bin/env python3
"""Smoke test — connect to the device via WDA and capture a screenshot.

Proves the WDA + Airtest path works for this project. Non-destructive.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked.
Run:  ./.venv/bin/python tests/connect_check.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.getLogger("airtest").setLevel(logging.WARNING)

import config                                        # noqa: E402
from airtest.core.api import connect_device          # noqa: E402


def main():
    os.makedirs(config.LOG, exist_ok=True)
    print(f"connecting: {config.DEVICE_URI}")
    dev = connect_device(config.DEVICE_URI)
    info = dev.display_info
    print(f"device up: {info['width']}x{info['height']} {info['orientation']}")

    out = os.path.join(config.LOG, "connect_check.png")
    dev.snapshot(filename=out)
    print(f"screenshot -> {out}")
    print("OK — WDA + Airtest working for this project.")


if __name__ == "__main__":
    main()
