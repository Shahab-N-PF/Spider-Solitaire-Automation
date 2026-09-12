#!/usr/bin/env python3
"""Test: declining Reset Statistics leaves local scores unchanged. [UNITY]

The reset confirmation is an in-app card, not a WDA alert. Its leftmost
button is No. This deliberately declines the operation and verifies that the
card closes, Statistics remains open, and the numbers region is unchanged.

This belongs immediately before resetStats in tests/run_all.py, while the
preceding tests have earned local scores and before the destructive reset.

Captures log/StatsResetCancelledBefore.png and
log/StatsResetCancelledAfter.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyResetCancelled.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_stats", settle=2.5),
              "Stats control not found on the menu")
    ui.expect(ui.at_screen("stats"),
              "tapping Stats did not open the Statistics screen")
    ui.expect(ui.scroll_to("reset_stats", max_swipes=12),
              "could not reach 'Reset Statistics'")

    before_path = ui.shoot("StatsResetCancelledBefore")
    ui.expect(ui.tap("reset_stats", settle=2.0),
              "'Reset Statistics' could not be tapped")
    ui.expect(ui.card_up(timeout=6.0),
              "tapping 'Reset Statistics' did not raise its confirmation card")
    buttons = ui.card_buttons()
    ui.expect(buttons,
              "the reset confirmation card has no detectable buttons")
    ui.expect(ui.answer_card(0, settle=2.0),
              "could not press No on the reset confirmation card")
    ui.expect(not ui.card_up(timeout=1.0),
              "the reset confirmation card remained open after pressing No")
    ui.expect(ui.at_screen("stats", timeout=4.0),
              "pressing No left the Statistics screen")

    after_path = ui.shoot("StatsResetCancelledAfter")
    w, h = ui.screen_size()
    # Exclude the status/header chrome and the bottom navigation edge. The
    # middle of this page contains the score blocks that a reset would erase.
    box = (0, int(h * 0.22), w, int(h * 0.86))
    before = ui.region(before_path, box)
    after = ui.region(after_path, box)
    difference = ui.diff_frac(before, after)
    ui.expect(difference <= 0.02,
              f"pressing No changed the Statistics numbers region by "
              f"{difference:.2%}; local scores may have been reset")

    ui.expect(ui.to_menu(),
              "could not return to the menu after cancelling reset")
    print(f"PASS: No cancelled Reset Statistics; score region diff "
          f"{difference:.2%} — {before_path}, {after_path}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
