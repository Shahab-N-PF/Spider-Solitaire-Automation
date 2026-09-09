#!/usr/bin/env python3
"""Test: first-launch links and pop-ups are handled through to the menu. [UNITY]

On a FRESH install, this opens the Terms & Conditions and Privacy Policy links
before Continue consumes the one-time card. Each link must reach its own page
and return to the card. Continue and the tracking prompt are then cleared.

It runs FIRST in tests/run_all.py. An already-visible first-launch gate is
preserved; otherwise Spider is cold-restarted. Whether or not the one-time card
appears, it puts the phone in Airplane Mode and hands every later test a clean
main menu. On a normal launch the link checks are skipped.

If the card appears but a bootstrap crop is missing, the test captures the
screen, reports the missing asset, and still clears the gates and leaves the
phone offline on the menu so the rest of run_all is not stranded.

Captures log/first_launch.png and, when applicable, the card and policy pages.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyFirstLaunch.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


LINKS = (
    ("terms", "tc_terms_link", "tc_terms_page", "Terms & Conditions"),
    ("privacy", "tc_privacy_link", "tc_privacy_page", "Privacy Policy"),
)
COOKIE_BUTTON = "Accept All Cookies"


def _start_without_clearing_overlays():
    """Start Spider without destroying a first-launch prompt already on screen."""
    sid = ui.launch(settle=1.5)
    # Installing and opening the build may already have started the genuine
    # first launch. Preserve either gate: killing the app while ATT is up can
    # dismiss/delay the sequence and make the policy-link check silently skip.
    if (ui.seen("tc_continue", timeout=4.0)
            or ui.seen("att_prompt", timeout=4.0)):
        return
    ui.terminate(sid)
    ui.sleep(1.5)
    ui.launch(force=True)


def _reveal_terms_card() -> bool:
    """Return True when T&C is up, allowing an ATT-first sequence if needed."""
    if ui.is_on("att_prompt"):
        ui.expect(ui.tap("att_allow", settle=2.0),
                  "the tracking prompt blocked the Terms & Conditions card")
        return ui.seen("tc_continue", timeout=12.0)
    if ui.seen("tc_continue", timeout=8.0):
        return True
    if ui.seen("att_prompt", timeout=8.0):
        ui.expect(ui.tap("att_allow", settle=2.0),
                  "the tracking prompt blocked the Terms & Conditions card")
        return ui.seen("tc_continue", timeout=12.0)
    return False


def _close_web_page() -> bool:
    """Close an in-app webview or return from an external browser."""
    if not ui.in_app():
        return ui.tap_back_to_app(settle=2.5)
    for name in ("Done", "Close", "BackButton"):
        if ui._tap_named("XCUIElementTypeButton", name):
            ui.sleep(2.0)
            return True
    if ui.have("tc_web_close") and ui.tap(
            "tc_web_close", timeout=1.0, settle=2.0):
        return True
    return ui.back(settle=2.0)


def _dismiss_cookie_banner(label: str) -> bool:
    """Accept the policy site's cookies when its banner is present."""
    kind = "XCUIElementTypeButton"
    if not ui._ax_first(kind, COOKIE_BUTTON, timeout=2.0):
        return False
    ui.expect(ui._tap_named(kind, COOKIE_BUTTON),
              f"could not tap {COOKIE_BUTTON} on the {label} page")
    for _ in range(10):
        if not ui._ax_first(kind, COOKIE_BUTTON, timeout=0.5):
            return True
        ui.sleep(0.5)
    raise AssertionError(
        f"{COOKIE_BUTTON} was tapped, but the cookie banner is still visible "
        f"on the {label} page")


def _walk_link(tag: str, link: str, page: str, label: str):
    missing = [name for name in (link, page) if not ui.have(name)]
    if missing:
        shot = ui.shoot("first_launch_terms_gate")
        verb = "is" if len(missing) == 1 else "are"
        raise AssertionError(
            f"the fresh-install card is up, but {', '.join(missing)} {verb} "
            f"missing from assets_unity. Crop the link and the {label} page "
            f"heading from this device before retrying (see {shot})")

    ui.expect(ui.tap(link, settle=3.0),
              f"could not tap the card's {label} link")
    shot = None
    try:
        if not ui.seen(page, timeout=12.0):
            failed = ui.shoot(f"first_launch_{tag}_page_failed")
            raise AssertionError(
                f"the {label} link did not open the expected page, or opened "
                f"the other policy page (see {failed})")
        _dismiss_cookie_banner(label)
        shot = ui.shoot(f"first_launch_{tag}_page")
    finally:
        where = f" (see {shot})" if shot else ""
        ui.expect(_close_web_page(),
                  f"could not close the {label} page{where}")
    ui.expect(ui.seen("tc_continue", timeout=8.0),
              f"closing the {label} page did not return to the Terms & "
              "Conditions card")
    print(f"  {label} link opened its page and returned to the card")


def _finish_on_offline_menu(card_was_up: bool) -> str:
    """Persist first-launch choices, go offline, and relaunch to the menu."""
    if card_was_up and not ui.is_on("tc_continue") and not ui.on_menu(timeout=1.0):
        # A failed page assertion must not strand the remaining suite in its
        # webview. Best-effort close; if that fails, background before killing
        # and reopening, preserving the same persistence rule as the happy path.
        _close_web_page()
        ui.resume()
        if not ui.seen("tc_continue", timeout=6.0):
            ui.home()
            ui.terminate()
            ui.sleep(1.0)
            ui.launch(force=True)
    ui.clear_overlays()
    if not ui.on_menu(timeout=6.0):
        ui.sleep(2.0)
        ui.clear_overlays()
    if card_was_up:
        ui.expect(ui.home(),
                  "Home did not background Spider before changing the network")

    offline = ui.offline(restore=False)
    if not offline:
        # Settings can rebuild its root page immediately after coming online;
        # one retry avoids turning that transient missed tap into a suite-wide
        # failure. Retry the whole radio operation: Airplane Mode alone is not
        # enough when iOS remembers that Wi-Fi was manually left enabled.
        offline = ui.offline(restore=False)
    ui.expect(offline,
              "could not enable Airplane Mode for the rest of run_all")
    ui.expect(ui.launch(force=True),
              "could not relaunch Spider after changing the network")
    ui.clear_overlays()
    ui.expect(ui.on_menu(timeout=10.0),
              "Spider did not relaunch to the main menu after going offline")
    return ui.shoot("first_launch")


def run():
    _start_without_clearing_overlays()
    card_was_up = _reveal_terms_card()
    failure = None
    try:
        if card_was_up:
            if ui.is_offline() is True:
                network = ui.online()
                ui.expect(network,
                          "the first-launch policy pages need Wi-Fi, but the "
                          "phone did not reconnect")
                ui.expect(ui.seen("tc_continue", timeout=8.0),
                          "the Terms & Conditions card disappeared while "
                          "bringing the phone online")
            for spec in LINKS:
                _walk_link(*spec)
        else:
            print("  no Terms & Conditions card — link checks skipped")
    except Exception as exc:  # clean up before run_all records the failure
        failure = exc

    shot = _finish_on_offline_menu(card_was_up)
    if failure:
        raise failure
    print("PASS: first launch checked the policy links when available, then "
          f"reached the main menu in Airplane Mode (see {shot})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
