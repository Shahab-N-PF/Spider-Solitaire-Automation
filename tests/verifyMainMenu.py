#!/usr/bin/env python3
"""Test: the main menu renders with all its expected controls. [UNITY]

The foundation test — if the menu doesn't render, nothing downstream can be
trusted. Asserts all seven menu controls plus the logo are on screen AT ONCE
rather than one at a time: a fresh launch slides a Game Center toast over the
menu and animates a sparkle across the labels, so any single anchor can be
briefly obscured. Polling the whole set is the real condition "the menu is up
and usable".

Spider's menu is Play / Stats / Options / Help / About (no "Daily") plus More
Games and Choose Look down the left, and the Spider logo is itself tappable.

Captures log/MainMenu.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyMainMenu.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    ui.expect(ui.launch_to_menu(), "did not reach the main menu after launch")

    anchors = list(ui.MENU_ITEMS) + ["menu_logo"]
    deadline = time.time() + 25.0
    missing = anchors
    while time.time() < deadline:
        missing = [a for a in anchors if not ui.is_on(a)]
        if not missing:
            break
        time.sleep(0.5)
    ui.expect(not missing, f"main-menu controls never all appeared: {missing}")

    shot = ui.shoot("MainMenu")
    print(f"PASS: main menu shows all {len(anchors)} controls "
          f"(Play/Stats/Options/Help/About + More Games/Choose Look + logo) "
          f"— see {shot}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
