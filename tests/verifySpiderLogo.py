#!/usr/bin/env python3
"""Test: the About screen, its links, and the tappable Spider logo. [UNITY]

Two entry points reach the same screen — the About menu item and the Spider logo
at the top of the menu — and both are checked, since the logo being tappable is
easy to lose in a port and invisible in a screenshot diff.

The outbound links (ad free version / more games / submit feedback) are asserted
present but NOT tapped: they leave the app for the App Store or a mail composer,
which would strand the suite outside the game. The FAQ link IS followed, because
it stays in-app.

The FAQ opened this way is then SCROLLED to its footer, the same way
verifyHelpPage scrolls Help. It runs a long way below the fold — the first
screenful ends mid-sentence — so a screenshot of the top proves almost nothing
about the rest of the body, and a port can render a header over an empty or
truncated list. Measured on an iPhone 11, build 363:

    swipes 1-10   content band moves 0.267 - 0.331   header moves <= 0.012
    swipe  11     content band moves 0.0000          bottom reached

The footer's "submit feedback" link is the anchor, because it is present at the
bottom (408, 1606) and absent from the top — so reaching it is itself the proof
that the page scrolled. The band excludes the fixed "FAQ" header bar, which is
what the header column above shows staying put.

Captures log/SpiderAboutPage.png, log/SpiderFAQ.png and log/SpiderFAQBottom.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifySpiderLogo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

LINKS = ("about_help", "about_faq", "about_feedback")

# ── scrolling the FAQ (see the module docstring for the measurements) ──
FAQ_BAND = (0.14, 0.94)         # content area, below the fixed "FAQ" header bar
FAQ_FOOTER = "about_feedback"   # the FAQ's last element; NOT on its first screen
FAQ_SWIPES = 20                 # 11 are needed on an iPhone 11 — headroom
MOVED = 0.05                    # a real swipe moves >= 0.267 of the band; the
                                # bottom one moves 0.0000, so this sits in open
                                # space and only has to tell those two apart


def faq_band(tag):
    """The FAQ's scrolling content as an image, minus the fixed header bar.

    Cropping the header out matters: it is about an eighth of the screen and it
    never moves, so leaving it in would dilute every measurement below towards
    "nothing happened".
    """
    w, h = ui.screen_size()
    return ui.region(ui.shoot(tag),
                     (0, int(h * FAQ_BAND[0]), w, int(h * FAQ_BAND[1])))


def run():
    # 1. About via the menu item.
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_about", settle=2.5), "About control not found on the menu")
    ui.expect(ui.at_screen("about"),
              "tapping About did not open the About screen (copyright line not found)")
    ui.expect(ui.is_on("about_version"), "the Version line is missing from About")
    shot = ui.shoot("SpiderAboutPage")

    missing = [name for name in LINKS if not ui.is_on(name)]
    ui.expect(not missing, f"About screen links missing: {missing}")
    print(f"  About shows the version, copyright and {len(LINKS)} links — see {shot}")

    # 2. The FAQ link stays in-app, so it is safe to follow.
    ui.expect(ui.tap("about_faq", settle=3.0), "the FAQ link could not be tapped")
    ui.expect(not ui.is_on("screen_about"),
              "tapping 'frequently asked questions' did not leave the About screen")
    faq = ui.shoot("SpiderFAQ")
    print(f"  FAQ opened from About — see {faq}")

    # 3. That FAQ has to scroll. The first screenful ends mid-answer, so the
    #    footer link is the only thing that proves the whole body came through.
    top_band = faq_band("_faq_top")
    reached = ui.scroll_to(FAQ_FOOTER, max_swipes=FAQ_SWIPES)
    moved = ui.diff_frac(top_band, faq_band("_faq_end"))
    ui.expect(reached,
              f"the FAQ opened from About never reached its footer ('submit "
              f"feedback') in {FAQ_SWIPES} swipes — " + (
                  f"and the page did not move at all (content changed "
                  f"{moved:.1%}; a real swipe changes 27%+), so the FAQ is NOT "
                  f"scrollable from this entry point"
                  if moved < MOVED else
                  f"it did scroll (content changed {moved:.1%}) but the footer "
                  f"never appeared, so the body may be truncated"))
    ui.expect(ui.is_on("about_back"),
              "scrolling the FAQ navigated away from it instead of moving its text")
    faq_bottom = ui.shoot("SpiderFAQBottom")
    print(f"  FAQ scrolls — reached its 'submit feedback' footer, see {faq_bottom}")

    ui.expect(ui.to_menu(), "could not get back to the main menu from the FAQ screen")

    # 4. The logo is a second, easily-broken route to the same screen.
    ui.expect(ui.tap("menu_logo", settle=2.5), "the menu logo could not be tapped")
    ui.expect(ui.at_screen("about"),
              "tapping the Spider logo did not open the About screen")
    print("  the menu logo opens About as well")

    ui.expect(ui.to_menu(), "could not return to the main menu after About")
    print("PASS: About reachable from both the About button and the logo; links "
          "present; FAQ opens in-app and scrolls to its footer")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
