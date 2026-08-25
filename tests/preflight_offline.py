#!/usr/bin/env python3
"""Preflight: confirm the device is OFFLINE before a capture / test run. [UNITY]

Live ads (the bottom banner, and the full-screen cross-promo interstitials that
interrupt screen transitions) are network-served and non-deterministic. They
pollute captures, and one of them fires reliably enough to make a functional path
untestable — opening Options from the in-game drawer was ad-interrupted on 3/3
attempts. So the functional suite runs with the device in Airplane Mode; WDA keeps
working because it runs over the USB cable (iproxy), not the network.

**Order matters:** start `scripts/wda.sh` FIRST, then go offline. WDA re-verifies
its developer certificate over the network when the runner launches, so starting
it while offline fails with "Developer App Certificate is not trusted".

Why this check is behavioral: iOS exposes no per-device reachability query over
USB, so we key off what is on screen — authoritatively, the Airplane-Mode icon in
the status bar. That needs a one-time crop per device/resolution, because it
can't be captured while online.

First-time calibration (once per device/resolution):
  1. Put the iPhone in Airplane Mode.
  2. Run this. With no airplane-icon template yet it captures
     log/preflight_offline.png and prints where to crop the glyph.
  3. Crop the status-bar airplane icon into assets/status_airplane.png (or
     iphone14/assets/, iphone7/portrait/assets/ for those devices). Re-run — it
     now asserts the icon is present.

The airplane glyph is drawn by iOS, not the app, so the crop is renderer-agnostic
and lives with the Obj-C `assets/` set rather than `assets_unity/`.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/preflight_offline.py
      DEVICE=iphone14 ./.venv/bin/python tests/preflight_offline.py   # iPhone 14
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import unity_ui as ui  # noqa: E402
from airtest.core.api import exists  # noqa: E402
from airtest.core.cv import Template  # noqa: E402

STATUS_AIRPLANE = "status_airplane"


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.sleep(3)                     # give a live ad time to load if we ARE online
    shot = ui.shoot("preflight_offline")

    tpl_path = os.path.join(config.ASSETS, STATUS_AIRPLANE + ".png")
    if not os.path.exists(tpl_path):
        print(f"NOTE: no airplane-icon template yet — this run only captured "
              f"evidence. To make this check reliable, crop the status-bar "
              f"airplane glyph from {shot} into {tpl_path}, then re-run.")
        raise AssertionError(
            "offline preflight needs a one-time calibration crop (see above)")

    # Matched with airtest directly, NOT through ui.find(): the airplane glyph is
    # an iOS status-bar element, not part of Unity's rendering, so it does not
    # follow Unity's width scaling and stays in the per-device ASSETS set.
    ui.expect(exists(Template(tpl_path, threshold=0.7)),
              f"the Airplane-Mode icon is not in the status bar — the device may "
              f"be ONLINE, which makes cross-promo interstitials interrupt the "
              f"run. Enable Airplane Mode and retry (WDA stays up over USB). "
              f"See {shot}")
    print(f"PASS: device looks OFFLINE (Airplane-Mode icon present) — see {shot}")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
