#!/usr/bin/env python3
"""Test: Options -> "Contact Us" opens Helpshift. [UNITY]

Two halves, because the suite runs offline and Helpshift will not load there:

  offline  — tapping Contact Us must still LEAVE Options. The capture is the
             no-network destination; the loaded page is not asserted.
             This is the `run()` that tests/run_all.py calls after Options.

  online   — the phone is brought onto the network, then Contact Us must leave
             Options AND show PeopleFun Support. run_all runs this last, after
             the offline suite, so ads cannot interrupt earlier tests.

    ./.venv/bin/python tests/verifyHelpShift.py            # both
    ./.venv/bin/python tests/verifyHelpShift.py --offline
    ./.venv/bin/python tests/verifyHelpShift.py --online

Captures log/HelpShift.png (offline) and log/HelpShiftOnline.png (online).

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

# Helpshift's header, measured on the Obj-C flow and the Unity SDK the same way:
# a native bar reading "PeopleFun Support". Predicate lookups, not a crop —
# the page is UIKit/WebView over Unity, so a template would bake in whatever
# sat behind it.
SUPPORT_TITLES = ("PeopleFun Support", "Helpshift")


def _leave_support() -> bool:
    """Close the Helpshift webview / hand-off, then walk back to the menu."""
    if not ui.in_app():
        ui.tap_back_to_app(settle=2.5)
    else:
        for name in ("Done", "Close", "BackButton"):
            if ui._tap_named("XCUIElementTypeButton", name):
                ui.sleep(1.5)
                break
        else:
            ui.back(settle=1.5)
    return ui.to_menu()


def _open_contact_us():
    """Walk menu -> Options -> Contact Us. Leaves the support destination up."""
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_options", settle=2.5),
              "Options control not found on the menu")
    ui.expect(ui.at_screen("options"), "the Options screen did not open")
    ui.expect(ui.is_on("contact_us"),
              "the 'Contact Us' button is missing from Options")
    ui.expect(ui.tap("contact_us", settle=4.0), "'Contact Us' could not be tapped")


def _support_title(timeout: float = 20.0) -> str:
    """Accessibility name of the Helpshift header, or '' if it never appeared."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for name in SUPPORT_TITLES:
            if ui._ax_first("XCUIElementTypeNavigationBar", name, timeout=1.5):
                return name
            if ui._ax_first("XCUIElementTypeStaticText", name, timeout=1.0):
                return name
        time.sleep(1.0)
    return ""


def run_offline():
    """Contact Us still redirects with no network. Does not pin the loaded page."""
    _open_contact_us()
    ui.sleep(4)                                  # no-network stand-in, settle
    shot = ui.shoot("HelpShift")
    ui.expect(not ui.is_on("screen_options"),
              "tapping 'Contact Us' did not leave the Options screen — the "
              "support redirect did not fire. "
              f"See {shot}")
    print(f"PASS: 'Contact Us' left Options for Helpshift (offline) — see {shot} "
          "(the loaded page is not asserted; it will not be PeopleFun Support)")
    ui.expect(_leave_support(),
              "could not return to the main menu from the support flow")


def run_online():
    """Bring the device online, then close Support and return via Options."""
    net = ui.online()
    ui.expect(bool(net),
              "could not leave Airplane Mode / join Wi-Fi — the online "
              "Helpshift check needs a network")
    print(f"  online on {net}")
    _open_contact_us()
    title = _support_title(timeout=24.0)
    shot = ui.shoot("HelpShiftOnline")
    ui.expect(not ui.is_on("screen_options"),
              "tapping 'Contact Us' did not leave the Options screen — the "
              "support redirect did not fire. "
              f"See {shot}")
    ui.expect(bool(title),
              "Contact Us left Options but PeopleFun Support did not load. "
              f"See {shot}")
    print(f"  'Contact Us' opened {title} (online on {net}) — see {shot}")

    # PeopleFun Support draws its own native header. On the iPhone 11 capture,
    # the top-left X is at (34, 82) in a 473x1024 frame, or (0.072w, 0.080h).
    # Use the relative position so this remains valid for the other 19.5:9
    # phones in the device family.
    w, h = ui.screen_size()
    ui.tap_at((int(w * 0.072), int(h * 0.080)), settle=2.5,
              reason="helpshift_support_x")
    ui.expect(ui.at_screen("options", timeout=8.0),
              "tapping the PeopleFun Support X did not return to Options")

    ui.expect(ui.tap("back_bar", settle=2.0),
              "the Options back button could not be tapped after closing "
              "PeopleFun Support")
    ui.expect(ui.on_menu(timeout=8.0),
              "the Options back button did not return to the main menu")
    final_shot = ui.shoot("HelpShiftOnlineAfter")
    print(f"PASS: 'Contact Us' opened {title}, then the Support X and Options "
          f"back returned to the main menu — see {shot}, {final_shot}")


def run(mode: str = "offline"):
    """run_all calls this with no args — that is the offline half."""
    if mode == "online":
        run_online()
    elif mode == "offline":
        run_offline()
    else:
        raise ValueError(f"unknown Helpshift mode {mode!r}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--offline", action="store_true",
        help="only the no-network redirect (what run_all calls after Options)")
    parser.add_argument(
        "--online", action="store_true",
        help="come online and assert PeopleFun Support loads")
    args = parser.parse_args(argv)
    if args.offline and not args.online:
        run_offline()
    elif args.online and not args.offline:
        run_online()
    else:
        run_offline()
        run_online()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
