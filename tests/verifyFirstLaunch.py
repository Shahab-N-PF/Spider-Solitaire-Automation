#!/usr/bin/env python3
"""Test: the first-launch pop-up sequence is handled through to the menu. [UNITY]

On a FRESH install the game shows, in order: a Terms & Conditions pop-up
(in-app, "Continue") and the iOS App Tracking Transparency prompt, then the main
menu. `ui.clear_overlays()` clears whatever is present — the ATT prompt through
WDA's alert API (it is a system alert, so it has real buttons WDA can read), and
any interstitial by its close control — and this asserts the menu is reached.

IMPORTANT — to actually exercise the pop-up path you must be on a first launch:
reinstall the app, or reset App Tracking (Settings > Privacy & Security >
Tracking) and clear the app's "agreed to terms" state. On a normal launch there
are no pop-ups and this simply confirms a cold start reaches the menu, which is
still worth having: it is the only test that starts from a terminated app rather
than walking back from wherever the previous test left off.

Captures log/first_launch.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyFirstLaunch.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    # Terminate first so this is a genuine cold start, not a warm foreground.
    reached = ui.cold_launch()
    shot = ui.shoot("first_launch")
    ui.expect(reached,
              "did not reach the main menu after a cold launch — a pop-up may "
              f"still be on screen (see {shot})")
    print(f"PASS: cold launch reached the main menu with no pop-ups left on "
          f"screen (see {shot})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
