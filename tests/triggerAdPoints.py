#!/usr/bin/env python3
"""Verify the five observed interstitial trigger points. [UNITY]

*** ONLINE only — deliberately not part of tests/run_all.py. ***

This test records two independent clocks:

* after more than 30 seconds on the game table, leaving the table for Options,
  Help, FAQ, or another destination can trigger an interstitial;
* after an interstitial is closed and the user is back in the game, a 30-second
  cooldown starts.

The five cases are exercised in order:

1. table for less than 30 seconds, then Options: no ad;
2. table for more than 30 seconds, then Help: ad;
3. table for more than 30 seconds, then QA Complete Game: ad on Victory;
4. close that Victory ad, tap New within 30 seconds: no ad;
5. win again, close the Victory ad, stay on Victory for more than 30 seconds,
   then tap New: ad.

An interstitial during ``resume_or_deal`` is also expected behavior. The test
closes its StoreKit X followed by the ad's own X and continues without a cold
launch. The ad-close crop is creative-dependent, so a missing close control is
reported rather than guessed.

Additional observed trigger: leaving a game can show an ad whose close returns
the user to the main menu. If the user remains on that menu for more than 30
seconds, the next resume or new deal can show another interstitial. This is a
separate menu dwell/cooldown path and must not be treated as a duplicate of
the original game-leave ad.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set,
         and a network connection.
Run:  ./.venv/bin/python tests/triggerAdPoints.py
      ./.venv/bin/python tests/triggerAdPoints.py --part cooldown
      ./.venv/bin/python tests/triggerAdPoints.py --part victory
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

SHORT = 8.0
DWELL = 32.0
NO_AD = 8.0
AD_WAIT = 20.0
STORE_WAIT = 120.0
AD_CLOSE_WAIT = 30.0


def close_current_ad(where: str):
    ui.expect(ui.in_app(),
              f"the {where} interstitial left Spider — now in "
              f"{ui.active_app() or 'unknown'}")
    ui.expect(ui.close_interstitial_chain(where, STORE_WAIT, AD_CLOSE_WAIT),
              f"could not close the {where} interstitial chain")


def reach_table(ad_attempts: int = 5):
    """Resume/deal, absorbing valid cooldown-expiry ads before the table."""
    for attempt in range(ad_attempts + 1):
        try:
            how = ui.resume_or_deal("easy")
            print(f"  {how}")
            ui.expect(ui.at_table(timeout=8.0),
                      "resume/deal finished without reaching the game table")
            return
        except AssertionError as e:
            if not (ui.lost() and ui.in_app()):
                raise
            print(f"  interstitial during resume_or_deal ({e}) — cooldown "
                  "expired, so the ad is expected before the table")
            close_current_ad("resume_or_deal")
            if attempt == ad_attempts:
                raise AssertionError(
                    "resume_or_deal kept producing interstitials without "
                    "eventually reaching the table")


def establish_fresh_table():
    """Start a new table so Rule 5 has a genuinely short dwell window."""
    reach_table()
    ui.settle_prompts()
    ui.expect(ui.at_table(), "could not establish the initial game table")

    # A previous standalone run may have left this table open past the
    # 30-second threshold. Deal a fresh table before starting the clocks. If
    # that New action itself triggers the stale-table ad, it proves the prior
    # cooldown expired. The ad is expected BEFORE the table: close it and keep
    # entering until a table is visible, then start Rule 5's short dwell clock.
    ui.expect(ui.open_ingame_menu(), "could not open the drawer for a fresh game")
    ui.expect(ui.tap("ingame_new", settle=3.0),
              "could not deal the fresh setup game")
    if ui.wait_lost(timeout=20.0):
        print("  fresh-game entry showed an interstitial — prior cooldown "
              "expired; closing it before waiting for the table")
        close_current_ad("fresh-table setup")
    ui.settle_prompts()
    if not ui.at_table(timeout=8.0):
        reach_table()
        ui.settle_prompts()
    ui.expect(ui.at_table(timeout=8.0),
              "could not reach a table after handling fresh-game entry ads")


def wait_no_ad(label: str, screen_check):
    """Assert the expected screen arrives without an interstitial."""
    deadline = time.time() + NO_AD
    while time.time() < deadline:
        ui.expect(ui.in_app(),
                  f"the app left Spider during the {label} no-ad window: "
                  f"{ui.active_app() or 'unknown'}")
        if screen_check():
            return
        ui.sleep(0.5)
    raise AssertionError(
        f"an interstitial appeared, or the expected screen did not settle, "
        f"during the {label} no-ad window")


def expect_ad(label: str):
    ui.expect(ui.wait_lost(timeout=AD_WAIT),
              f"no interstitial appeared for {label} within {AD_WAIT:.0f}s")
    close_current_ad(label)


def open_drawer_action(anchor: str, label: str):
    ui.expect(ui.open_ingame_menu(),
              f"the game drawer did not open before {label}")
    ui.expect(ui.tap(anchor, settle=2.0),
              f"could not tap the drawer's {label} action")


def verify_short_options_no_ad(retries: int = 1):
    """Rule 5, retrying once when inherited cooldown produces an entry ad."""
    for attempt in range(retries + 1):
        print(f"  rule 5: waiting {SHORT:.0f}s before opening Options"
              + (" (clean retry)" if attempt else ""))
        ui.sleep(SHORT)
        try:
            open_drawer_action("ingame_options", "Options")
        except AssertionError:
            if not (ui.in_app() and ui.lost(timeout=1.0)):
                raise

        deadline = time.time() + NO_AD
        while time.time() < deadline:
            ui.expect(ui.in_app(),
                      "the app left Spider during the short table -> Options "
                      f"window: {ui.active_app() or 'unknown'}")
            if ui.at_screen("options", timeout=0.5):
                back_to_table()
                print("  rule 5 passed: short table visit did not trigger an ad")
                return
            if ui.lost(timeout=0.5):
                break
            ui.sleep(0.3)
        else:
            raise AssertionError(
                "Options did not settle during the short-table no-ad window")

        if attempt == retries:
            raise AssertionError(
                "an interstitial appeared during short table -> Options even "
                "after resetting the inherited cooldown")
        print("  short table -> Options inherited an expired cooldown; "
              "closing that setup ad and retrying from a visible table")
        close_current_ad("short table -> Options setup retry")
        back_to_table()
        ui.expect(ui.at_table(timeout=8.0),
                  "could not restore the table for the clean Rule 5 retry")


def back_to_table():
    """Return from a destination without restarting Spider."""
    if ui.at_table(timeout=4.0):
        return
    if ui.at_screen("options", timeout=2.0) or ui.at_screen("help", timeout=2.0):
        ui.expect(ui.back(), "could not return from the destination screen")
        ui.expect(ui.at_table(timeout=8.0),
                  "destination back did not return to the game table")
        return
    reach_table()
    ui.settle_prompts()
    ui.expect(ui.at_table(timeout=8.0),
              "could not restore the table without a cold launch")


def win_and_expect_victory_ad(label: str):
    """Win the active table through the QA panel and require its ad."""
    ui.expect(ui.win_current_game(timeout=12.0),
              f"QA Complete Game did not reach Victory for {label}")
    ui.expect(ui.close_dev_panel(),
              f"could not collapse the Dev Panel on Victory for {label}")
    expect_ad(label)
    ui.expect(ui.at_screen("victory", timeout=8.0),
              f"the {label} ad did not leave the Victory screen visible")


def ensure_dev_panel():
    """Make the Dev Panel available without repeating its unlock gesture."""
    if ui.is_on("dev_complete_game"):
        print("  Dev Panel is already open — skipping enable steps")
        return
    if ui.is_on("dev_panel"):
        ui.expect(ui.open_dev_panel(from_menu=False),
                  "the visible Dev Panel button could not be expanded")
        return
    if not ui.on_menu(timeout=2.0):
        ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.open_dev_panel(),
              "could not enable the Dev Panel")


def clear_startup_overlays():
    """Close leftover debugger/Dev Panel UI before classifying an ad."""
    if ui.on_window("Select Live Network", timeout=2.0):
        ui.expect(ui._tap_named("XCUIElementTypeButton", "BackButton"),
                  "could not leave the leftover Select Live Network window")
        ui.sleep(2)
    if ui.on_max_debugger(timeout=2.0):
        ui.expect(ui.close_max_debugger(),
                  "could not close the leftover MAX debugger")
    if ui.is_on("dev_complete_game"):
        ui.expect(ui.close_dev_panel(),
                  "could not collapse the leftover Dev Panel")


def prepare():
    """Bring the device online and establish the shared clean table state."""
    net = ui.online()
    ui.expect(net,
              "the device could not be brought online — MAX/interstitial "
              "coverage needs Wi-Fi")
    print(f"  device is online — Wi-Fi joined {net!r}")

    ui.launch()
    clear_startup_overlays()
    if ui.lost(timeout=2.0):
        close_current_ad("leftover")

    # The Dev Panel is a prerequisite for both synthetic wins. Reuse it when
    # it is already open or its button is already visible; only enable it when
    # neither is showing.
    ensure_dev_panel()
    ui.expect(ui.close_dev_panel(), "could not collapse the Dev Panel")

    establish_fresh_table()
    return net


def run_cooldown_rules():
    """Short Options suppression and long Help trigger."""
    # Rule 5: under 30 seconds on the table, redirect to Options -> no ad.
    # One inherited-cooldown ad is setup noise: close it, restore the table,
    # restart the short dwell clock, and require the clean retry to pass.
    verify_short_options_no_ad()

    # Rule 4: over 30 seconds on the table, redirect to Help -> ad.
    print(f"  rule 4: waiting {DWELL:.0f}s before opening Help")
    ui.sleep(DWELL)
    open_drawer_action("ingame_help", "Help")
    expect_ad("long table -> Help")
    back_to_table()
    print("  rule 4 passed: long table redirect triggered an ad")


def run_victory_rules():
    """Victory trigger plus inside/outside-cooldown New behavior."""
    # Rule 1: over 30 seconds on the table, complete it -> Victory ad.
    print(f"  rule 1: waiting {DWELL:.0f}s before Complete Game")
    ui.sleep(DWELL)
    win_and_expect_victory_ad("long table -> Victory")
    print("  rule 1 passed: long table visit triggered an ad on Victory")

    # Rule 2: the 30-second post-ad cooldown suppresses New.
    ui.expect(ui.tap("victory_new", settle=3.0),
              "Victory's New button could not be tapped inside cooldown")
    wait_no_ad("Victory ad closed -> New within cooldown",
               lambda: ui.at_table(timeout=0.5))
    ui.settle_prompts()
    ui.expect(ui.at_table(timeout=12.0),
              "New within the cooldown did not reach a game table")
    print("  rule 2 passed: New within 30s did not trigger an ad")

    # Rule 3: after another win/ad, remain on Victory past the cooldown, then
    # New must trigger the interstitial.
    print(f"  rule 3: waiting {DWELL:.0f}s before the second win")
    ui.sleep(DWELL)
    win_and_expect_victory_ad("second long table -> Victory")
    print(f"  rule 3: waiting {DWELL:.0f}s on Victory for cooldown expiry")
    ui.sleep(DWELL)
    ui.expect(ui.tap("victory_new", settle=3.0),
              "Victory's New button could not be tapped after cooldown")
    expect_ad("Victory -> New after cooldown")
    back_to_table()
    print("  rule 3 passed: New after 30s on Victory triggered an ad")


def run(part: str = "all"):
    net = prepare()
    if part in ("all", "cooldown"):
        run_cooldown_rules()
    if part in ("all", "victory"):
        run_victory_rules()

    if part == "all":
        result = "all five interstitial trigger/cooldown rules"
    elif part == "cooldown":
        result = "the short/long table cooldown rules"
    else:
        result = "the Victory trigger/cooldown rules"
    print(f"PASS: {result} passed online on {net!r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part", choices=("all", "cooldown", "victory"),
                        default="all",
                        help="run all rules or one independently-runnable group")
    args = parser.parse_args()
    try:
        run(args.part)
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
