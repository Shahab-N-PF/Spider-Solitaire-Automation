#!/usr/bin/env python3
"""Test: the victory screen. [UNITY]

Steps:
  1. win a game using the QA cheat (Dev Panel -> Complete Game);
  2. close the Dev Panel so its overlay isn't covering what we assert on;
  3. assert the victory screen renders all of its parts;
  4. assert the footer names the level that was actually played;
  5. leave via the screen's own "back" control, landing on the main menu.

Why a cheat and not a real win: winning Spider legitimately takes hundreds of
correct moves, which no UI test can drive. The Obj-C suite used that build's QA
cheat for the same reason. The Unity equivalent is the Dev Panel's "Complete
Game", wrapped as ui.win_game(). Without it the victory screens are untestable.

REQUIRES tests/openDebugTools.py TO HAVE RUN FIRST. This test does not perform
the unlock gesture itself (win_game(arm=False)) — openDebugTools owns it, and
repeating it here was duplicated work. That hand-off only holds because
helpers.launch_app() no longer restarts the app between tests, so the revealed
Dev Panel button survives. Anything that DOES restart the app (a cold_launch
recovery, launch_to_menu(force=True), reinstalling the build) hides the button
again and this test will stop before touching the victory screen, saying so.

The level check is the assertion worth having. Any build shows *a* victory
screen; this one has to report the level the game was actually dealt at, which
catches the screen being rendered from stale or default state.

Step 5 exits by the victory screen's own "back" control. It USED to tap "new"
(which deals a fresh game) and exit from the table, so leaving by back was a path
the suite never took — and taking it turned up that build 363 had changed the
control: the crops cut from 353-era captures no longer match it. It is now the
same small green-felt back as the About screen (about_back, 0.992).

Note what is no longer covered: nothing on the victory screen is now PRESSED to
prove it works. "new" is still in PARTS, so it must still render — it is just not
tapped any more. Leaving by back also leaves NO game in progress, which is what
lets tests/verifyDifficultyLevels.py start at Medium without an abandon prompt.

Note this test WRITES to local statistics — it records a win. That is inherent
to testing a victory screen, and it is why the run also proves the counters are
reachable rather than asserting exact values.

Captures log/VictoryScreen.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyVictory.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

LEVEL = "easy"

# Everything the screen must render. Split out so a failure names the missing
# element instead of just "the victory screen looks wrong".
PARTS = {
    "victory_ranking":      "the 'ranking for' header",
    "screen_victory":       "the current/rank/best column headers",
    "victory_leaderboards": "the leaderboards link",
    "victory_achieve":      "the achievements link",
    "victory_help":         "the help button",
    "victory_new":          "the new button",
    "victory_stats":        "the stats button",
}


def run():
    # 1-2. win via the QA cheat, then get the panel overlay out of the way — it
    #      sits over the right-hand column, which is where the stats button is.
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.is_on("dev_panel"),
              "the Dev Panel button is not showing, so the cheat this test needs "
              "is not available. Run tests/openDebugTools.py first — it performs "
              "the unlock gesture. (Note a restart of the app hides the button "
              "again, so nothing may cold-launch in between.)")
    ui.expect(ui.win_game(LEVEL, arm=False),
              f"could not win a {LEVEL} game with the Dev Panel cheat")
    ui.expect(ui.close_dev_panel(), "could not close the Dev Panel overlay")
    shot = ui.shoot("VictoryScreen")

    # 3. every element renders.
    missing = [f"{d} ({n})" for n, d in PARTS.items() if not ui.is_on(n)]
    ui.expect(not missing,
              f"the victory screen is missing {len(missing)} element(s): "
              f"{'; '.join(missing)} — see {shot}")
    print(f"  victory screen renders all {len(PARTS)} elements")

    # 4. it reports the level actually played, not a default.
    ui.expect(ui.is_on(f"victory_level_{LEVEL}"),
              f"the victory screen does not report '{LEVEL} level' in its footer, "
              f"so it is not reflecting the game that was just played — see {shot}")
    print(f"  footer reports '{LEVEL} level' — matches the game played")

    # 5. leave by the screen's own back control. ui.back() taps whichever back
    #    template is on screen; on build 363 the victory screen's is the same
    #    small green-felt control as About's, which about_back matches at 0.992.
    ui.expect(ui.back(settle=2.5),
              f"the victory screen's 'back' control was not found, so there is no "
              f"way off it — see {shot}")
    # back may land on the menu directly or on the table it came from; either is
    # fine, so long as the menu is reachable. to_menu() is a no-op once there.
    ui.expect(ui.to_menu(),
              "tapping 'back' on the victory screen did not lead to the main menu")
    print("  'back' leaves the victory screen and reaches the main menu")

    print(f"PASS: the victory screen renders and can be left — see {shot}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
