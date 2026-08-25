#!/usr/bin/env python3
"""Test: the hidden QA/debug gesture on the About screen. [UNITY]

Steps:
  1. open About from the main menu;
  2. confirm the Dev Panel button is NOT showing yet;
  3. tap the spider emblem 5 times rapidly — the hidden gesture;
  4. assert the "Dev Panel" button is now showing, in the bottom-right corner.

WHERE you tap decides whether this works. The gesture is on the spider EMBLEM
only: a 5-tap burst on the emblem reveals the button, while the identical burst
on the "Spider SOLITAIRE" wordmark ~50 px below changes 0.00% of the screen.
An earlier version of this test aimed at about_logo (the wordmark) and concluded
the QA entry point had been dropped in the Unity port — it had not, it was being
tapped in the wrong place. Hence about_emblem is its own crop, and the tap goes
to its centre rather than to an offset from the wordmark.

The taps also have to be genuinely rapid. A loop of ordinary airtest taps runs at
~510 ms each (>2.5 s for five) — outside the detection window — so it would
report the gesture as absent purely by driving it too slowly. ui.rapid_tap()
sends the whole burst as ONE W3C Actions request executed on-device (~70-120 ms
per tap) and returns False if it ever falls back, which this test asserts on
BEFORE it judges the app: a slow burst makes a negative result meaningless.

Two behaviours worth knowing, both verified on the device:
  * the gesture TOGGLES — a second 5-tap burst hides the button again, so this
    test fires exactly ONE burst and leaves the Dev Panel showing;
  * the button, once unlocked, appears on EVERY screen (only the gesture is tied
    to About) and stays until the app is RESTARTED — no screen scoping involved.

That second point is why this test starts with launch_to_menu(force=True) while
the rest of the suite does not. The suite deliberately stops restarting the app
between tests, so state survives (tests/verifyVictory.py reuses the unlock this
test performs). But this test's premise is that the button is hidden until the
gesture reveals it, and only a restart makes that true — without the force it
would fail on a re-run, having found its own previous unlock still on screen.

Captures log/debug_tools.png (the About screen with the Dev Panel button).

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/openDebugTools.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

TAPS = 5


def run():
    # 1. About.
    # force: the premise is a hidden button, which only a restart guarantees.
    ui.expect(ui.launch_to_menu(force=True), "could not reach the main menu")
    ui.expect(ui.tap("menu_about", settle=2.5), "About control not found on the menu")
    ui.expect(ui.at_screen("about"), "tapping About did not open the About screen")

    # 2. Precondition: the button is hidden until the gesture. Without this the
    #    test would pass on a build that simply always shows it.
    ui.expect(not ui.is_on("dev_panel"),
              "the Dev Panel button is already showing on the About screen before "
              "the gesture — it is supposed to be hidden until unlocked")

    # 3. Five rapid taps on the EMBLEM (not the wordmark — see the docstring).
    ui.expect(ui.is_on("about_emblem"),
              "the Spider emblem is not on the About screen, so the QA gesture "
              "has nothing to tap")
    x, y = ui.find("about_emblem")
    fast = ui.rapid_tap((x, y), times=TAPS)
    ui.expect(fast,
              "the tap burst fell back to per-tap WDA calls (~510 ms each), so it "
              "was not a rapid gesture and this result is inconclusive — check "
              "that the WDA /actions endpoint is reachable")

    # 4. The Dev Panel button must now be showing, bottom-right.
    shot = ui.shoot("debug_tools")
    pos = ui.find("dev_panel")
    ui.expect(pos is not None,
              f"tapping the Spider emblem {TAPS}x rapidly did not reveal the "
              f"'Dev Panel' button — the hidden QA entry point is unreachable. "
              f"See {shot}")

    w, h = ui.screen_size()
    ui.expect(pos[0] > w * 0.5 and pos[1] > h * 0.5,
              f"the 'Dev Panel' button appeared at {pos}, not in the bottom-right "
              f"corner of the {w}x{h} screen — see {shot}")
    print(f"  {TAPS} rapid taps on the About emblem revealed the 'Dev Panel' "
          f"button at {pos} (bottom-right) — see {shot}")

    # The button is deliberately LEFT ON — no toggle-off burst. It is there to
    # inspect after the run, and tests/verifyVictory.py depends on it: it uses
    # this unlock instead of repeating the gesture, which works because the suite
    # no longer restarts the app between tests.
    ui.to_menu()
    print("PASS: the hidden QA entry point is present on the About screen")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
