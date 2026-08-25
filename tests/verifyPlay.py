#!/usr/bin/env python3
"""Test: Play opens the difficulty picker and deals a game.

Spider's Play doesn't deal directly — it opens a picker (Easy / Medium / Hard /
Bold / Expert). This asserts all five levels render, then deals Easy and proves
the TABLE came up, not merely that the picker went away: choosing a level while
another game is paused raises an "abandon?" confirmation, which also leaves the
picker, so a "picker gone" check would pass while sitting on a dialog.

Run:  ./.venv/bin/python tests/verifyPlay.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.open_picker(), "tapping Play did not open the difficulty picker")
    shot_p = ui.shoot("DifficultyLevels")

    missing = [d for d in ui.DIFFICULTIES if not ui.is_on(f"difficulty_{d}")]
    ui.expect(not missing, f"difficulty levels missing from the picker: {missing}")
    print(f"  picker shows all {len(ui.DIFFICULTIES)} levels — {shot_p}")

    ui.expect(ui.start_game("easy"),
              "choosing Easy did not reach the game table (in-game bar not found)")
    shot_t = ui.shoot("Play")

    print(f"PASS: Play -> picker (5 levels) -> Easy dealt a game — {shot_t}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
