#!/usr/bin/env python3
"""Test: every difficulty level deals a playable game.

verifyPlay.py covers Easy; this covers all five, because the levels differ in how
many suits are dealt and a port can break one while the others work. Each level
is driven end to end (menu -> Play -> level -> table), and a failure on one level
is recorded rather than aborting, so a single run reports exactly which levels
are broken.

Each level also has to clear the "abandon the currently paused game?"
confirmation, since the previous level's game is still open — ui.start_game()
answers it.

Run:  ./.venv/bin/python tests/verifyDifficultyLevels.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    failures = []
    for level in ui.DIFFICULTIES:
        try:
            ui.expect(ui.launch_to_menu(), f"[{level}] could not reach the main menu")
            ui.expect(ui.open_picker(), f"[{level}] the difficulty picker did not open")
            ui.expect(ui.start_game(level),
                      f"[{level}] choosing it did not reach the game table")
            shot = ui.shoot(f"unity_difficulty_{level}")
            print(f"PASS: {level:7} dealt a game — {shot}")
        except Exception as e:  # noqa: BLE001 — cover every level in one run
            print(f"FAIL: {level:7} — {e}")
            failures.append(level)

    if failures:
        raise AssertionError(
            f"{len(failures)}/{len(ui.DIFFICULTIES)} level(s) failed: " + ", ".join(failures))
    print(f"PASS: all {len(ui.DIFFICULTIES)} difficulty levels deal a game")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
