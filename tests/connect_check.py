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


def preflight():
    """Name the likely cause before airtest raises something cryptic.

    This is the FIRST thing SETUP.md asks a newcomer to run, so a raw traceback
    here is the worst possible first impression — and airtest's own message
    ("iOS devices not found") points at the device when the real cause is
    usually that WDA was never started.
    """
    problems = []
    try:
        import urllib.request
        urllib.request.urlopen(config.WDA_URL + "/status", timeout=8)
    except Exception:  # noqa: BLE001
        problems.append(
            f"WDA is not answering at {config.WDA_URL}.\n"
            "      Start it in another terminal and LEAVE IT RUNNING:\n"
            "          ./scripts/wda.sh <YOUR-UDID>\n"
            "      The iPhone must be plugged in and UNLOCKED.")
    if not config.DEVICE_UDID:
        problems.append(
            "DEVICE_UDID is not set, so airtest will grab the first device it can\n"
            "      see — including WiFi-paired phones that are not plugged in:\n"
            "          export DEVICE_UDID=<the same UDID you gave scripts/wda.sh>")
    return problems


def main():
    print(f"connecting: {config.DEVICE_URI}")
    os.makedirs(config.LOG, exist_ok=True)
    dev = connect_device(config.DEVICE_URI)
    info = dev.display_info
    print(f"device up: {info['width']}x{info['height']} {info['orientation']}")

    out = os.path.join(config.LOG, "connect_check.png")
    dev.snapshot(filename=out)
    print(f"screenshot -> {out}")
    print("OK — WDA + Airtest working for this project.")


if __name__ == "__main__":
    problems = preflight()
    if problems:
        print("cannot connect yet:")
        for p in problems:
            print(f"  - {p}")
        print("\n  Full setup instructions: SETUP.md")
        sys.exit(2)
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"\nFAILED to connect: {e}\n")
        print("  WDA answered, so the usual causes are:")
        print("    - the iPhone is LOCKED (unlock it and re-run)")
        print("    - DEVICE_UDID names a phone that is not plugged in")
        print("    - the developer certificate is not trusted on the phone")
        print("      (Settings -> General -> VPN & Device Management)")
        print("\n  More: SETUP.md -> Troubleshooting")
        sys.exit(1)
