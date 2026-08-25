#!/usr/bin/env python3
"""Test: the Options screen — sections, scrolling, and a live toggle. [UNITY]

Goes past "the screen opened": Options is a settings surface, so this walks the
whole (below-the-fold) page to confirm all three sections render, and flips a
toggle to confirm the control is actually live rather than just painted.

A toggle exposes no accessibility state on Unity, so "did it flip?" is answered
from pixels: capture the toggle's neighbourhood before and after and require it
to change. That is a weaker claim than reading a boolean, but a real one — a
dead control produces an identical image. The setting is restored afterwards so
the test leaves no trace.

Captures log/OptionsPage.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyOptions.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

SECTIONS = ("opt_sounds", "opt_cards", "opt_interface")


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_options", settle=2.5), "Options control not found on the menu")
    ui.expect(ui.at_screen("options"),
              "tapping Options did not open the Options screen ('options' title not found)")
    ui.expect(not ui.on_menu(timeout=1.0), "tapping Options did not leave the main menu")
    shot = ui.shoot("OptionsPage")

    # The support entry point lives in this screen's top bar.
    ui.expect(ui.is_on("contact_us"), "the 'Contact Us' button is missing from Options")

    for name in SECTIONS:
        ui.expect(ui.scroll_to(name, max_swipes=10),
                  f"the '{name}' section was never reached while scrolling Options")
        print(f"  section present: {name}")

    # Flip the first toggle under the Cards section and require a visible change.
    # The toggle sits right-aligned on the first row below the section header;
    # both offsets are fractions of the screen (measured from the Unity layout)
    # rather than hardcoded pixels, so they hold across the 19.5:9 devices.
    ui.expect(ui.scroll_to("opt_cards", max_swipes=10), "could not return to the Cards section")
    x, y = ui.find("opt_cards")
    w, h = ui.screen_size()
    toggle = (int(w * 0.808), y + int(h * 0.066))
    before = _crop(ui.shoot("_opt_before"), toggle)
    ui.tap_at(toggle, settle=1.5)
    after = _crop(ui.shoot("_opt_after"), toggle)
    ui.expect(_differs(before, after),
              "tapping the first Cards toggle changed nothing on screen — "
              "the control may be dead")
    ui.tap_at(toggle, settle=1.5)               # restore the original setting

    ui.expect(ui.to_menu(), "could not return to the main menu after Options")
    print(f"PASS: Options opened, all {len(SECTIONS)} sections reachable, "
          f"Contact Us present, a toggle responds (see {shot})")


def _crop(path, centre, half=90):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    x, y = centre
    return im.crop((max(0, x - half), max(0, y - half),
                    min(im.width, x + half), min(im.height, y + half)))


def _differs(a, b, min_frac=0.02):
    import numpy as np
    ia, ib = np.asarray(a, dtype=np.int16), np.asarray(b, dtype=np.int16)
    if ia.shape != ib.shape:
        return True
    return float((np.abs(ia - ib).max(axis=2) > 12).mean()) > min_frac


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
