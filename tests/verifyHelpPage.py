#!/usr/bin/env python3
"""Test: Help opens from the main menu and we can return. [UNITY]

Asserts we left the menu AND that the "Introduction" heading is on screen (so we
opened the right sub-screen, not just any), screenshots it into log/HelpPage.png,
then returns to the menu.

Also scrolls the rules text to the bottom, since the Help page runs well below
the fold and a port can render the header while leaving the body empty — the
footer's FAQ link is the proof the whole scrollable body came through.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyHelpPage.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_help", settle=2.5), "Help control not found on the menu")
    ui.expect(ui.at_screen("help"),
              "tapping Help did not open the Help screen "
              "('Introduction' heading not found)")
    ui.expect(not ui.on_menu(timeout=1.0), "tapping Help did not leave the main menu")
    shot = ui.shoot("HelpPage")

    # The rules run below the fold; reaching the footer proves the body rendered.
    ui.expect(ui.scroll_to("about_faq", max_swipes=12),
              "never reached the bottom of the Help page (its FAQ link)")
    bottom = ui.shoot("HelpPageBottom")

    ui.expect(ui.to_menu(), "could not return to the main menu after Help")
    print(f"PASS: Help opened (verified 'Introduction'), scrolled to the bottom, "
          f"and returned to the menu (see {shot}, {bottom})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
