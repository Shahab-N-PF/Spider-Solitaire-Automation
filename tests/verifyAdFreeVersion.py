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
App Store, and comes back without killing the app, so in-app state survives.
This applies the same route to a link on About — but returns the way a PERSON
does, by tapping the "◀ Spider" crumb iOS draws in the status bar, rather than
asking WDA to foreground the app. Note that crumb is BIDIRECTIONAL: it names
whichever app you came from, so ui.tap_back_to_app() refuses to tap when the
game is already in front, or it would throw the run OUT of the game.

**The link does not go straight out.** It raises a confirmation card first —
"Would you like to take a look at the Ad free version? / Tap Yes to proceed to
the App Store" with **No / Yes**. This test first answers **No** and proves the
card only dismisses while Spider remains on About, then answers **Yes** and
proves only Yes hands off. That was not obvious
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

# The paid build this link must land on, as a substring of the App Store page
# title (ui.store_title() strips the '▻' glyph the store injects into it).
# Asserted as well as the bundle id: the id only says "an App Store page",
# and the point of an ad-free link is WHICH product it reaches.
EXPECTED_TITLE = "Spider Solitaire +"


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

    # 6. First take the negative path. No must dismiss only the card and keep
    #    Spider in front on the About screen.
    buttons = ui.card_buttons()
    ui.expect(len(buttons) == 2,
              f"the ad-free card should offer two buttons (No, Yes) but "
              f"{len(buttons)} were found at {buttons} — the wrong card may "
              "be up")
    ui.expect(ui.answer_card(0, settle=2.0),
              "could not press No on the ad-free card")
    no_shot = ui.shoot("AdFreeVersionNo")
    ui.expect(ui.active_app() == config.BUNDLE_ID,
              "pressing No on the ad-free card left Spider")
    ui.expect(ui.at_screen("about", timeout=5.0),
              "pressing No on the ad-free card did not leave About on screen")
    print(f"  No dismissed the card and stayed on About — see {no_shot}")

    # 7. Answer Yes — index 1, the RIGHT-hand pill. Index 0 is No, and taking it
    #    would dismiss the card and pass nothing on to the store.
    ui.expect(ui.tap(LINK, settle=2.5),
              "the 'ad free version' link could not be tapped a second time")
    ui.expect(ui.card_up(timeout=6.0),
              "the second 'ad free version' tap did not raise its confirmation")
    buttons = ui.card_buttons()
    ui.expect(len(buttons) == 2,
              f"the ad-free card should offer two buttons (No, Yes) but "
              f"{len(buttons)} were found at {buttons} — the wrong card may be "
              f"up, and answering it blind could tap the wrong thing")
    ui.expect(ui.answer_card(1, settle=4.0), "could not press Yes on the ad-free card")
    print("  the link raises a No/Yes card; answered Yes")

    # 8. Now it should hand off. The bundle id is the assertion, not the pixels.
    went_to = ui.left_app()
    ui.expect(went_to == ui.APP_STORE,
              f"answering Yes on the ad-free card did not open the App Store — "
              f"the foreground app is {went_to or 'unknown'}. " + (
                  "The app never left, even though the card promised 'Tap Yes "
                  "to proceed to the App Store'."
                  if went_to == config.BUNDLE_ID else
                  f"It went somewhere, but to {went_to}, not "
                  f"{ui.APP_STORE}."))

    # 9. Now the page is worth capturing — and worth NAMING. The bundle id only
    #    says "an App Store page"; the title says WHICH product, and the whole
    #    point of an ad-free link is that it lands on this game's paid build
    #    rather than any other page the store could have shown.
    shot = ui.shoot("AdFreeVersion")
    title = ui.store_title()
    ui.expect(EXPECTED_TITLE.lower() in title.lower(),
              f"the App Store opened, but on {title!r} rather than a page named "
              f"{EXPECTED_TITLE!r} — the link reaches the store but not this "
              f"game's paid build. (An empty title means the page had not "
              f"rendered, not that the link is wrong.) See {shot}")
    print(f"  'ad free version' opened the App Store on {title!r} — see {shot}")

    # 10-11. Come back the way a PERSON does: tap the "◀ Spider" crumb iOS draws
    #       in the status bar, rather than asking WDA to foreground the app.
    #       Landing back on ABOUT is then what proves the app was never
    #       relaunched — the App Store is an overlay Spider survives underneath.
    ui.expect(ui.tap_back_to_app(),
              "tapping the '◀ Spider' breadcrumb in the status bar did not bring "
              "the game back from the App Store. That crumb is drawn by iOS, not "
              "by the store, so it has no accessibility entry to fall back on — "
              f"check the top-left of {shot} for it.")
    ui.expect(ui.at_screen("about", timeout=10.0),
              "came back from the App Store but not to the About screen — if "
              "this is the main menu, the app was RESTARTED rather than resumed, "
              "and any in-app state a run depends on is gone")
    print("  switching back returns to About, with the app still running")

    # 12-13. Leave the app where every other test expects to find it.
    ui.expect(ui.to_menu(), "could not return to the main menu after About")
    print(f"PASS: About's 'ad free version' opens the App Store and switching "
          f"back returns to About (see {shot})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
