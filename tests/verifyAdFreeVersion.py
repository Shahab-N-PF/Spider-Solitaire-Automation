#!/usr/bin/env python3
"""Test: About's "ad free version" link opens the App Store. [UNITY]

**ONLINE only, and deliberately NOT in tests/run_all.py** — see the reason in
run_all's "Not in the suite, on purpose" block. The hand-off itself works
offline, but the whole point of this test is the page it lands on, and offline
every link lands on the same "No Internet Connection" screen. A screenshot of
that proves nothing.

The About screen carries five links, and verifySpiderLogo follows only the FAQ
one, because that one stays in-app; its docstring says the others are not tapped
since they would "strand the suite outside the game". verifyMoreGamesIcons
answered that objection — it taps five promo icons, proves each hands off to the
App Store, and comes back with ui.resume(), which foregrounds Spider WITHOUT
killing it, so in-app state survives. This applies the same route to a link on
About.

**The link does not go straight out.** It raises a confirmation card first —
"Would you like to take a look at the Ad free version? / Tap Yes to proceed to
the App Store" with **No / Yes** — and only Yes hands off. That was not obvious
from the About screen and it is the reason a first version of this test reported
the link as dead: 20 seconds of sampling after the tap showed the foreground app
never changing, while the screen had in fact changed 100% (the app dims the felt
behind the card, so nearly every pixel moves).

That card is the widget CLAUDE.md already documents — pale mint, black text,
translucent, and shipped in one- and two-button forms — so it is found by SHAPE
(ui.card_dialog / ui.card_buttons), never by a template, and answered by
POSITION: index 0 is the dismissing button in every instance measured on this
build, so **Yes is index 1**. Measured here: card at (94, 728, 640, 362), pills
at x=266 (No) and x=562 (Yes).

Two things this checks that a screenshot cannot:

  * WHICH APP we landed in. No capture can tell you that — an App Store page and
    an in-app mock-up of one are the same pixels to a template — so the
    foreground bundle id is the assertion (ui.left_app()).
  * That we came back to ABOUT, the screen we left from. That is the proof the
    app was RESUMED rather than restarted; a relaunch would land on the menu.

All five About links share a font, a colour and a centre line (x=413 on an
iPhone 11), so position cannot tell them apart — the link is found by its own
glyphs, via assets_unity/about_adfree.png, cut from this build's own rendering
at box (266, 1236, 562, 1276) of log/SpiderAboutPage.png.

Captures log/AdFreeVersion.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set,
         device ONLINE.
Run:  ./.venv/bin/python tests/verifyAdFreeVersion.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import unity_ui as ui  # noqa: E402

LINK = "about_adfree"


def run():
    # 1-3. Reach About, and prove we are on it rather than merely off the menu.
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_about", settle=2.5), "About control not found on the menu")
    ui.expect(ui.at_screen("about"),
              "tapping About did not open the About screen (copyright line not found)")

    # 4. Assert the link EXISTS before tapping it, so "the link is missing" and
    #    "the link goes nowhere" stay two different failures.
    ui.expect(ui.is_on(LINK),
              "the 'ad free version' link is not on the About screen — the other "
              "four links are checked by verifySpiderLogo, so if they are there "
              "and this one is not, the link itself has been dropped")

    # 5. Tap it — which opens a confirmation card rather than leaving the app.
    ui.expect(ui.tap(LINK, settle=2.5), "the 'ad free version' link could not be tapped")
    ui.expect(ui.card_up(timeout=6.0),
              "tapping 'ad free version' did not raise the "
              "'Would you like to take a look at the Ad free version?' card, so "
              "the link did nothing at all")

    # 6. Answer Yes — index 1, the RIGHT-hand pill. Index 0 is No, and taking it
    #    would dismiss the card and pass nothing on to the store.
    buttons = ui.card_buttons()
    ui.expect(len(buttons) == 2,
              f"the ad-free card should offer two buttons (No, Yes) but "
              f"{len(buttons)} were found at {buttons} — the wrong card may be "
              f"up, and answering it blind could tap the wrong thing")
    ui.expect(ui.answer_card(1, settle=4.0), "could not press Yes on the ad-free card")
    print("  the link raises a No/Yes card; answered Yes")

    # 7. Now it should hand off. The bundle id is the assertion, not the pixels.
    went_to = ui.left_app()
    ui.expect(went_to == ui.APP_STORE,
              f"answering Yes on the ad-free card did not open the App Store — "
              f"the foreground app is {went_to or 'unknown'}. " + (
                  "The app never left, even though the card promised 'Tap Yes "
                  "to proceed to the App Store'."
                  if went_to == config.BUNDLE_ID else
                  f"It went somewhere, but to {went_to}, not "
                  f"{ui.APP_STORE}."))

    # 8. Now the page is worth capturing.
    shot = ui.shoot("AdFreeVersion")
    print(f"  'ad free version' opened the App Store ({went_to}) — see {shot}")

    # 9-10. Come back. resume() foregrounds Spider without restarting it, so
    #       landing back on ABOUT is what proves the app was not relaunched.
    ui.expect(ui.resume(),
              "could not switch back to Spider from the App Store")
    ui.expect(ui.at_screen("about", timeout=10.0),
              "came back from the App Store but not to the About screen — if "
              "this is the main menu, the app was RESTARTED rather than resumed, "
              "and any in-app state a run depends on is gone")
    print("  switching back returns to About, with the app still running")

    # 11-12. Leave the app where every other test expects to find it.
    ui.expect(ui.to_menu(), "could not return to the main menu after About")
    print(f"PASS: About's 'ad free version' opens the App Store and switching "
          f"back returns to About (see {shot})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
