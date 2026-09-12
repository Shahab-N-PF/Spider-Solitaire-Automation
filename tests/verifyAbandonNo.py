#!/usr/bin/env python3
"""Test: declining the abandon prompt keeps the difficulty picker open. [UNITY]

Choosing a difficulty while a game is paused raises an abandon confirmation.
The negative path matters because answering No must cancel only that new deal;
it must not silently start a game, leave the picker, or discard the paused game.

The test leaves the paused game in place for the next test. If it is run
standalone without an existing game, it creates one first and returns to the
menu before exercising the confirmation.

Captures log/AbandonNo.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyAbandonNo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def _ensure_paused_game():
    """Leave a paused game behind while returning to the main menu."""
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.open_picker(), "could not open the difficulty picker")

    # A suite run reaches this test from verifyPlay with an active Easy game.
    # Opening the picker from the menu exposes the Resume ribbon in that case.
    if ui.seen("resume", timeout=2.0):
        return

    # Standalone runs may have no saved game. Deal one, leave the table, and
    # open the picker again so the same negative path is exercised.
    ui.expect(ui.start_game("easy"),
              "could not create a game for the abandon negative case")
    ui.expect(ui.to_menu(), "could not return to the menu with a paused game")
    ui.expect(ui.open_picker(), "could not reopen the difficulty picker")
    ui.expect(ui.seen("resume", timeout=4.0),
              "the paused game did not produce a Resume option")


def run():
    _ensure_paused_game()

    # Tap the same level that is already paused. Do not call start_game(): it
    # intentionally answers this alert Yes, while this test must answer No.
    ui.expect(ui.tap("difficulty_easy", settle=1.5),
              "could not tap Easy in the difficulty picker")
    ui.expect(ui.dialog_up(timeout=4.0),
              "choosing Easy over a paused game did not raise a confirmation")
    text = ui.alert_now().lower()
    ui.expect("abandon" in text,
              f"the picker raised the wrong confirmation: {text or 'unknown'}")

    ui.expect(ui.answer_dialog(False),
              "could not answer No on the abandon confirmation")
    ui.expect(ui.at_screen("difficulty", timeout=5.0),
              "declining abandon did not leave the difficulty picker open")
    ui.expect(not ui.at_table(timeout=1.0),
              "declining abandon unexpectedly started a new game")
    shot = ui.shoot("AbandonNo")

    # The picker has no Back button; its logo is the documented route back.
    ui.expect(ui.to_menu(),
              "could not return to the menu after declining abandon")
    print(f"PASS: No cancelled the new deal and kept the paused game — {shot}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
