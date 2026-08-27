#!/usr/bin/env python3
"""Test: every difficulty level deals a playable game.

The levels differ in how many suits are dealt, so a port can break one while the
others work. Each level is driven end to end (menu -> Play -> level -> table),
and a failure on one level is recorded rather than aborting, so a single run
reports exactly which levels are broken.

Starts at MEDIUM. Easy is not lost from the suite: verifyPlay.py asserts the
picker renders all five levels and deals Easy, and verifyVictory.py deals Easy
for its cheat win.

The "abandon the currently paused game?" confirmation still has to be cleared,
but no longer on every level. In suite order this test follows verifyVictory,
which finishes its game and leaves via "back" without dealing another — so
nothing is paused when Medium is chosen and no prompt appears. Hard, Bold and
Expert each still find the previous level's game open, and a STANDALONE run can
start with anything paused, so ui.start_game() keeps answering it either way.

Run:  ./.venv/bin/python tests/verifyDifficultyLevels.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

# Deliberately not ui.DIFFICULTIES: that tuple is the full set the PICKER must
# render, which verifyPlay.py asserts against. This is the subset this test
# deals, and it starts at Medium.
LEVELS = ("medium", "hard", "bold", "expert")


def run():
    failures = []
    for level in LEVELS:
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
            f"{len(failures)}/{len(LEVELS)} level(s) failed: " + ", ".join(failures))
    print(f"PASS: all {len(LEVELS)} difficulty levels ({LEVELS[0]}..{LEVELS[-1]}) "
          f"deal a game")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
