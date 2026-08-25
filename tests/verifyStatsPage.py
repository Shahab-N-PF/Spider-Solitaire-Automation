#!/usr/bin/env python3
"""Test: Stats opens from the main menu, renders, scrolls, and returns. [UNITY]

Asserts we left the menu AND that the "Statistics" header is on screen (so we
opened the right sub-screen, not just any), then scrolls the whole page to the
"Reset Statistics" link at the very bottom — reaching it proves every
per-difficulty block rendered, not just the header.

Non-destructive: the reset link is located but NOT tapped. Actually resetting is
tests/resetStats.py, which is deliberately kept out of the default suite.

Captures log/StatsPage.png and log/StatsResetBtn.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyStatsPage.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_stats", settle=2.5), "Stats control not found on the menu")
    ui.expect(ui.at_screen("stats"),
              "tapping Stats did not open the Statistics screen "
              "('Statistics' title not found)")
    ui.expect(not ui.on_menu(timeout=1.0), "tapping Stats did not leave the main menu")
    shot = ui.shoot("StatsPage")

    ui.expect(ui.is_on("game_center"),
              "the Game Center button is missing from the Statistics header")
    ui.expect(ui.scroll_to("reset_stats", max_swipes=12),
              "never reached 'Reset Statistics' at the bottom of the Statistics page")
    bottom = ui.shoot("StatsResetBtn")

    ui.expect(ui.to_menu(), "could not return to the main menu after Stats")
    print(f"PASS: Statistics opened (verified 'Statistics' header + Game Center), "
          f"scrolled to 'Reset Statistics' (not tapped), and returned "
          f"(see {shot}, {bottom})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
