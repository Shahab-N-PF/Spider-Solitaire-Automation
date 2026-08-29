#!/usr/bin/env python3
"""Test: resetting local statistics (DESTRUCTIVE).

Scrolls to the "Reset Statistics" link at the bottom of the Statistics page,
taps it, and accepts every confirmation. Spider asks twice ("reset local
scores?" then a "just to be on the safe side" double-check), so the accept loop
is written to survive the app adding or dropping a step rather than hardcoding
two.

DESTRUCTIVE: this permanently clears local statistics on the device (Game Center
scores are untouched, per the dialog).

It runs LAST in tests/run_all.py, which is what makes that safe: everything that
reads or depends on play history has already run — verifyStatsPage renders the
page, verifyDifficultyLevels banks four wins, and verifyMoreGamesIcons needs at
least one completed game before the promo strip is drawn at all. Each run
re-earns that before reaching here, so wiping at the end leaves the next run's
ordering intact. Note the consequence: a full suite run now ends with the
device's local statistics at zero.

Run:  ./.venv/bin/python tests/resetStats.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_stats", settle=2.5), "Stats control not found on the menu")
    ui.expect(ui.at_screen("stats"), "the Statistics screen did not open")

    ui.expect(ui.scroll_to("reset_stats", max_swipes=12),
              "could not reach 'Reset Statistics' at the bottom of the page")
    ui.expect(ui.tap("reset_stats", settle=2.0), "'Reset Statistics' could not be tapped")

    ui.expect(ui.dialog_up(timeout=6.0),
              "tapping 'Reset Statistics' did not raise a confirmation dialog")
    shot = ui.shoot("ResetStats")

    confirmed = 0
    while confirmed < 5 and ui.dialog_up(timeout=3.0):
        ui.expect(ui.answer_dialog(True), "could not accept a reset confirmation")
        confirmed += 1
    ui.expect(confirmed >= 1, "no reset confirmation was accepted")
    print(f"  accepted {confirmed} confirmation dialog(s) — {shot}")

    ui.expect(ui.to_menu(), "did not get back to the main menu after resetting")
    print("PASS: local statistics reset and returned to the main menu")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
