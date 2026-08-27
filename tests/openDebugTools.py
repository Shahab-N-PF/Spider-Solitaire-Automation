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
  * the unlock is scoped to the ABOUT SCREEN on build 363. Measured in a single
    process with no restart anywhere: gesture on About -> button shows; to_menu()
    -> gone; return to About without a new gesture -> still gone; expanding the
    panel first does not save it either. An earlier note here claimed the button
    "appears on EVERY screen and stays until the app is RESTARTED" — that was
    true of build 353 and is NOT true now.

This test does NOT restart the app. It used to (launch_to_menu(force=True)), to
guarantee its "the button is hidden" precondition on a re-run. That is no longer
needed: the unlock dies when you leave About, and step 6 leaves to the menu, so a
completed run always leaves it hidden. The trade-off, stated: a run that DIES on
the About screen with the button showing will make the next run fail at step 2.
Re-running after any such failure needs the app backgrounded once, or the gesture
repeated to toggle the button off.

Note the second bullet is why tests/verifyVictory.py can no longer reuse this
unlock: "Complete Game" only acts on an ACTIVE game and must be fired from the
table, but the panel does not survive the trip there.

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
    # 1. About. No restart — attach to the app as it is (see the docstring).
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_about", settle=2.5), "About control not found on the menu")
    ui.expect(ui.at_screen("about"), "tapping About did not open the About screen")

    # 2. Locate the EMBLEM (not the wordmark — see the docstring). Needed before
    #    the precondition, because clearing it uses the same gesture.
    ui.expect(ui.is_on("about_emblem"),
              "the Spider emblem is not on the About screen, so the QA gesture "
              "has nothing to tap")
    x, y = ui.find("about_emblem")

    # 3. Precondition: the button must be hidden before the gesture, or this test
    #    would pass on a build that simply always shows it.
    #
    #    An earlier run can legitimately leave it ON — the unlock persists, which
    #    is the whole point of the openDebugTools -> verifyVictory hand-off. This
    #    used to be handled by restarting the app; the test no longer does that,
    #    so it clears the button the way a user would: the gesture TOGGLES, so one
    #    burst turns it off. That also exercises the toggle-off direction, which
    #    nothing else covered.
    if ui.is_on("dev_panel"):
        print("  Dev Panel was already unlocked — toggling it off first")
        ui.expect(ui.rapid_tap((x, y), times=TAPS),
                  "the tap burst fell back to per-tap WDA calls while trying to "
                  "clear a previous unlock")
        ui.expect(not ui.is_on("dev_panel"),
                  "a second 5-tap burst did not hide the Dev Panel button — the "
                  "gesture is supposed to toggle")

    ui.expect(not ui.is_on("dev_panel"),
              "the Dev Panel button is showing on the About screen before the "
              "gesture and could not be cleared — it is supposed to be hidden "
              "until unlocked")

    # 4. Five rapid taps on the emblem — the gesture itself.
    fast = ui.rapid_tap((x, y), times=TAPS)
    ui.expect(fast,
              "the tap burst fell back to per-tap WDA calls (~510 ms each), so it "
              "was not a rapid gesture and this result is inconclusive — check "
              "that the WDA /actions endpoint is reachable")

    # 5. The Dev Panel button must now be showing, bottom-right.
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

    # 6. Back to the menu, by the screen's own back control. The button is
    #    deliberately LEFT ON — no toggle-off burst — so it can be inspected
    #    after the run. (It does not survive this trip on build 363; see the
    #    docstring. The burst is still not repeated: the gesture toggles.)
    ui.expect(ui.back(settle=2.0),
              "the About screen's back control was not found, so there was no "
              "way off it")
    ui.expect(ui.on_menu(timeout=6.0),
              "tapping 'back' on the About screen did not return to the main menu")
    print("  'back' returned to the main menu, Dev Panel button left ON")
    print("PASS: the hidden QA entry point is present on the About screen")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
