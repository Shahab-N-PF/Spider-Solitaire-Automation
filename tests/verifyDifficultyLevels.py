#!/usr/bin/env python3
"""Test: every difficulty level deals a playable game, and can be WON. [UNITY]

Per level: menu -> Play -> the level -> the game table -> win it with the QA
cheat -> the victory screen -> leave by that screen's own "back" control.
A failure on one level is recorded rather than aborting, so a single run reports
exactly which levels are broken.

Starts at MEDIUM. Easy is not lost from the suite: verifyPlay.py asserts the
picker renders all five levels and deals Easy, and verifyVictory.py deals Easy
for its cheat win.

REQUIRES THE DEV PANEL, so tests/openDebugTools.py must have run first — that
test owns the 5-tap unlock gesture. ensure_cheat() will perform the unlock itself
if the button is missing (so a standalone run works), but in suite order it
should already be showing. Note anything that RESTARTS the app hides the button
again; ensure_cheat() runs per level so one lost unlock does not doom the rest.

The "abandon the currently paused game?" confirmation no longer appears at all in
suite order: every level's game is COMPLETED before the next one starts, so
nothing is ever left paused. ui.start_game() keeps answering it anyway, for a
standalone run that begins with a game already open.

Note this test WRITES to local statistics — it records four wins. That is
inherent to winning four games, and it is why nothing here asserts exact counter
values. It also satisfies verifyMoreGamesIcons' precondition (the promo strip
only draws once at least one game has been completed).

Captures log/unity_difficulty_<level>.png and log/unity_victory_<level>.png.

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
            play_and_win(level)
            print(f"PASS: {level:7} dealt, won via the cheat, and left by 'back'")
        except Exception as e:  # noqa: BLE001 — cover every level in one run
            print(f"FAIL: {level:7} — {e}")
            failures.append(level)
        finally:
            # ALWAYS collapse the panel, pass or fail. Expanded, its overlay
            # covers the right-hand column — which is where the main menu draws
            # the labels on_menu() looks for, and where the picker draws
            # Hard/Bold/Expert. Left up after a failure, the next level's
            # launch_to_menu() would fail to see the menu and fall back to
            # cold_launch(), restarting the app and hiding the Dev Panel button
            # for every level after it. One line, and it stops that cascade.
            try:
                ui.close_dev_panel()
            except Exception as e:  # noqa: BLE001 — must not mask the real failure
                print(f"  WARNING: could not close the Dev Panel overlay ({e})")

    if failures:
        raise AssertionError(
            f"{len(failures)}/{len(LEVELS)} level(s) failed: " + ", ".join(failures))
    print(f"PASS: all {len(LEVELS)} difficulty levels ({LEVELS[0]}..{LEVELS[-1]}) "
          f"deal a game, win it, and return to the menu")


def play_and_win(level: str):
    """Deal `level`, win it with the QA cheat, and leave via the victory screen."""
    ui.expect(ui.launch_to_menu(), f"[{level}] could not reach the main menu")
    ensure_cheat(level)

    ui.expect(ui.open_picker(), f"[{level}] the difficulty picker did not open")
    ui.expect(ui.start_game(level),
              f"[{level}] choosing it did not reach the game table")
    shot = ui.shoot(f"unity_difficulty_{level}")
    print(f"  {level}: dealt a game — {shot}")

    ui.expect(ui.win_current_game(),
              f"[{level}] the Dev Panel's 'Complete Game' cheat did not lead to "
              f"the victory screen — see {shot}")
    # Close the overlay BEFORE capturing, so the shot shows the victory screen
    # rather than the panel sitting over it.
    ui.expect(ui.close_dev_panel(), f"[{level}] could not close the Dev Panel overlay")
    won = ui.shoot(f"unity_victory_{level}")
    print(f"  {level}: won via the cheat — {won}")

    # Leave the way verifyVictory does: back may land on the menu directly or on
    # the table it came from, so assert the tap landed and then that the menu is
    # reachable. to_menu() is a no-op once already there.
    ui.expect(ui.back(settle=2.5),
              f"[{level}] the victory screen's 'back' control was not found, so "
              f"there is no way off it — see {won}")
    ui.expect(ui.to_menu(),
              f"[{level}] tapping 'back' on the victory screen did not lead to "
              f"the main menu")


def ensure_cheat(level: str):
    """Make sure the Dev Panel button is showing, arming it if it is not.

    Called per level rather than once, because a mid-run app restart (an ad
    recovery, a cold_launch fallback) hides the button and would otherwise leave
    every remaining level failing for a reason that reads like a game bug.
    """
    if ui.is_on("dev_panel"):
        return
    print(f"  {level}: Dev Panel button not showing — performing the unlock")
    ui.expect(ui.open_dev_panel(),
              f"[{level}] the Dev Panel button is not showing and the unlock "
              f"gesture did not reveal it, so the cheat this test needs is "
              f"unavailable. Run tests/openDebugTools.py first.")
    ui.expect(ui.close_dev_panel(),
              f"[{level}] could not collapse the Dev Panel after arming it")
    # open_dev_panel() drives to the About screen to perform the gesture, so the
    # caller's "we are on the menu" is no longer true — walk back before it taps
    # Play.
    ui.expect(ui.to_menu(),
              f"[{level}] could not return to the main menu after arming the cheat")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
