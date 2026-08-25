#!/usr/bin/env python3
"""Test: the About screen, its links, and the tappable Spider logo. [UNITY]

Two entry points reach the same screen — the About menu item and the Spider logo
at the top of the menu — and both are checked, since the logo being tappable is
easy to lose in a port and invisible in a screenshot diff.

The outbound links (ad free version / more games / submit feedback) are asserted
present but NOT tapped: they leave the app for the App Store or a mail composer,
which would strand the suite outside the game. The FAQ link IS followed, because
it stays in-app.

Captures log/SpiderAboutPage.png and log/SpiderFAQ.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifySpiderLogo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

LINKS = ("about_help", "about_faq", "about_feedback")


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
    ui.expect(ui.to_menu(), "could not get back to the main menu from the FAQ screen")

    # 3. The logo is a second, easily-broken route to the same screen.
    ui.expect(ui.tap("menu_logo", settle=2.5), "the menu logo could not be tapped")
    ui.expect(ui.at_screen("about"),
              "tapping the Spider logo did not open the About screen")
    print("  the menu logo opens About as well")

    ui.expect(ui.to_menu(), "could not return to the main menu after About")
    print("PASS: About reachable from both the About button and the logo; links "
          "present; FAQ opens in-app")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
