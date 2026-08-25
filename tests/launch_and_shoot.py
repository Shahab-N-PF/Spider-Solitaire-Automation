#!/usr/bin/env python3
"""Launch the game and screenshot it — the starting point for real flows.

Opens the app by its bundle ID, waits for it to settle, and captures a
screenshot you can crop template assets from (save them into assets/).

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, BUNDLE_ID set in config.py.
Run:  ./.venv/bin/python tests/launch_and_shoot.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.getLogger("airtest").setLevel(logging.WARNING)

import config                                          # noqa: E402
import helpers                                          # noqa: E402
from airtest.core.api import connect_device, snapshot, sleep    # noqa: E402


def main():
    if not config.bundle_id_is_set():
        print("Set BUNDLE_ID in config.py first (or export BUNDLE_ID=...).")
        print("Find it with: ./.venv/bin/python -m tidevice applist")
        sys.exit(1)

    os.makedirs(config.LOG, exist_ok=True)

    # Launch via WDA session (reliably foregrounds the app on iOS).
    print(f"launching: {config.BUNDLE_ID} ({config.GAME_NAME})")
    sid = helpers.launch_app()
    print(f"  session: {sid}")
    sleep(3.0)  # let the game splash/menu settle

    # Airtest then drives whatever is on screen.
    print(f"connecting: {config.DEVICE_URI}")
    connect_device(config.DEVICE_URI)

    out = os.path.join(config.LOG, "launch.png")
    snapshot(filename=out)
    print(f"screenshot -> {out}")
    print("Next: crop buttons/cells from this image into assets/, then")
    print("      touch(Template('assets/xxx.png')) to drive the game.")


if __name__ == "__main__":
    main()
