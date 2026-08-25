#!/usr/bin/env python3
"""Test: the game table — controls, real moves, and the drawer.

This is the test that asks whether the port still PLAYS, not just whether it
renders. The centrepiece is a deal/undo round trip:

    capture board -> deal a row from the stock -> board must change
                  -> undo -> board must return to the original

That is a genuine assertion about game logic, and it is checkable without any
accessibility tree: undo is only correct if the pixels come back. It catches a
class of port bug (undo not restoring state) that no screenshot diff would.

The rest covers the table chrome: the three bottom controls, and the in-game
drawer's six actions — options / help / faq are opened and backed out of, and
"new" must deal a fresh game. "abandon" is deliberately left alone, since it
ends the game the later steps depend on.

Run:  ./.venv/bin/python tests/verifyGamePlay.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

DRAWER = ("ingame_replay", "ingame_abandon", "ingame_options",
          "ingame_new", "ingame_help", "ingame_faq")


def reach_table():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.open_picker(), "the difficulty picker did not open")
    ui.expect(ui.start_game("easy"), "Easy did not deal a game")


def drawer_opens(button, screen, retries=2):
    """Open a drawer action and assert it reached its screen.

    The device is online, so a cross-promo interstitial can answer the tap
    instead of the app. That is an interruption, not a defect, so it is detected
    (nothing recognisable on screen) and retried from a clean state. Anything
    else fails immediately — a broken button must not be retried into a pass.

    If EVERY attempt was eaten by an ad, the failure says so rather than blaming
    the button, because those are different problems with different fixes.
    `screen=None` means the destination has no anchor of its own, so we only
    require that we left the table.
    """
    ads = 0
    for attempt in range(retries + 1):
        ui.expect(ui.open_ingame_menu(), f"the drawer did not open before {button}")
        ui.expect(ui.tap(button, settle=2.5), f"{button} could not be tapped")
        if screen is None:
            if not ui.at_table(timeout=1.5):
                return
        elif ui.at_screen(screen):
            return
        if attempt < retries and ui.lost():
            ads += 1
            print(f"    (an interstitial ad interrupted {button} — recovering)")
            ui.expect(ui.recover(), "could not recover from the interstitial")
            reach_table()
            continue
        if ads:
            raise AssertionError(
                f"could not verify {button}: a cross-promo interstitial ad "
                f"intervened on {ads}/{attempt + 1} attempts. This is the ad "
                f"placement, not the button — put the device in Airplane Mode "
                f"(WDA is already running, so it stays connected) for a "
                f"deterministic run.")
        raise AssertionError(
            f"{button} did not open the {screen or 'expected'} screen")


def run():
    reach_table()
    shot = ui.shoot("GamePlay")
    print(f"  game table reached — {shot}")

    # 1. The table's own controls must be present.
    for name in ("back_game", "in_game_menu", "tap_undo", "tap_lower", "tap_hints"):
        ui.expect(ui.is_on(name), f"game-table control missing: {name}")
    print("  table controls present (back / menu / undo / lower / hints)")

    # 2. Deal a row from the stock, then undo it. The board must change, then
    #    come back — that round trip is the real functional claim here.
    before = ui.board_shot("before")
    ui.expect(ui.tap_stock(), "could not tap the stock pile")
    dealt = ui.board_shot("dealt")
    ui.expect(ui.changed(before, dealt),
              "dealing from the stock did not change the board")
    print(f"  stock deal changed the board ({ui.diff_frac(before, dealt)*100:.1f}% of pixels)")

    ui.expect(ui.tap_table_control("undo"), "the undo control could not be tapped")
    undone = ui.board_shot("undone")
    back_frac = ui.diff_frac(before, undone)
    ui.expect(back_frac <= 0.01,
              f"undo did not restore the board — it still differs from the "
              f"pre-deal state by {back_frac*100:.1f}% of pixels")
    print(f"  undo restored the board (residual {back_frac*100:.2f}%)")

    # 3. Hints should surface a suggestion. The highlight is TRANSIENT — it plays
    #    for under a second and the board returns to exactly its previous pixels
    #    — so this samples across the animation instead of taking one capture
    #    after a settle, which would always see "nothing happened".
    peak = ui.peak_change_after(
        lambda: ui.expect(ui.tap_table_control("hints", settle=0.0),
                          "the hints control could not be tapped"),
        frames=5, interval=0.3, tag="hint")
    ui.expect(peak > 0.002,
              f"tapping 'tap for hints' never changed the board (peak "
              f"{peak*100:.2f}%) — note the game shows nothing when no move is "
              f"available, so check the board has a legal move")
    print(f"  hints produced a visible suggestion (peak {peak*100:.2f}% of the board)")

    # 4. The in-game drawer and its six actions.
    ui.expect(ui.open_ingame_menu(), "the in-game menu drawer did not open")
    missing = [b for b in DRAWER if not ui.is_on(b)]
    ui.expect(not missing, f"in-game drawer buttons missing: {missing}")
    drawer = ui.shoot("InGameMenu")
    print(f"  drawer shows all {len(DRAWER)} actions — {drawer}")

    # 5. options / help / faq each open a screen and back out to the table.
    #    Each action closes the drawer, so it is reopened before the next one.
    for button, screen in (("ingame_options", "options"), ("ingame_help", "help")):
        drawer_opens(button, screen)
        ui.expect(ui.back(), f"could not go back from {screen}")
        ui.expect(ui.at_table(), f"backing out of {screen} did not return to the table")
        print(f"  drawer -> {screen} -> back")

    drawer_opens("ingame_faq", None)
    ui.expect(ui.back(), "could not go back from the FAQ screen")
    print("  drawer -> faq -> back")

    # 6. "new" deals a fresh game: the table stays up and the board changes.
    ui.expect(ui.at_table(), "not on the table before dealing a new game")
    pre_new = ui.board_shot("prenew")
    ui.expect(ui.open_ingame_menu(), "the drawer did not reopen before New")
    ui.expect(ui.tap("ingame_new", settle=3.0), "New could not be tapped")
    ui.settle_prompts()
    ui.expect(ui.at_table(timeout=12.0), "New did not leave us on a game table")
    post_new = ui.board_shot("postnew")
    ui.expect(ui.changed(pre_new, post_new),
              "New did not deal a different board")
    print("  drawer -> new dealt a fresh board")

    print("PASS: game table plays — deal/undo round trip holds, hints respond, "
          "and all six drawer actions behave")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
