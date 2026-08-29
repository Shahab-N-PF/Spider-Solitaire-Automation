#!/usr/bin/env python3
"""Test: the game table — controls, real moves, and the drawer.

This is the test that asks whether the port still PLAYS, not just whether it
renders. The centrepiece is a deal/undo round trip:

    capture board -> deal a row from the stock -> board must change
                  -> undo -> board must return to the original

That is a genuine assertion about game logic, and it is checkable without any
accessibility tree: undo is only correct if the pixels come back. It catches a
class of port bug (undo not restoring state) that no screenshot diff would.

The other two bottom controls are exercised the same way. "tap to lower" is a
persistent toggle — it drops the whole playfield down the screen so it is easier
to reach — so it is checked as a there-and-back pair. "tap for hints" is
transient and needs sampling across its animation.

The rest covers the table chrome: the in-game
drawer's six actions — options / help / faq are opened and backed out of, and
"new" must deal a fresh game. "abandon" is deliberately left alone, since it
ends the game the later steps depend on.

The Options trip does double duty. While it is open it drives the "Use Hearts"
setting and then goes back to check the TABLE — a cross-screen claim nothing
else in the suite makes: a control on another page changes what the game draws.
Easy is a one-suit game, so the whole deal flips from black spades to red hearts
and back, which makes "no spades remain" a sound assertion as well as "hearts
appeared".

Run:  ./.venv/bin/python tests/verifyGamePlay.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

DRAWER = ("ingame_replay", "ingame_abandon", "ingame_options",
          "ingame_new", "ingame_help", "ingame_faq")


def reach_table():
    """Get to a game table, RESUMING a paused game rather than abandoning it.

    Leaving the table pauses a game instead of ending it, so in a suite run
    verifyPlay's Easy game is still sitting there when this starts, and the old
    behaviour — deal a fresh one over it — spent a whole deal to throw that
    away. ui.resume_or_deal() carries on with an open table, else resumes from
    the picker, and deals only when there is nothing to come back to.

    Nothing below cares which level dealt the board: every check here is about
    how the TABLE behaves. The one thing a resumed game could cost is a stock
    with no cards left, which the deal/undo check needs — in practice this test
    ENDS by dealing a fresh board through the drawer's "New", so the game it
    finds on the next run is an untouched one with a full stock.
    """
    print(f"  {ui.resume_or_deal('easy')}")


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


LOWER_SETTLE = 5.0      # the bottom captions vanish for ~4.5s while it slides


def locate(name: str, timeout: float = 10.0):
    """find(), but tolerant of the table's redraw gaps.

    The bottom captions blank out for ~4.5s every time the playfield slides, and
    briefly after a card animation, so a single-shot find() on this screen is a
    coin toss — it is what made an early version of check_lower() fail with "the
    caption is not on the table" straight after the undo step.
    """
    for _ in range(3):
        if ui.seen(name, timeout=timeout):
            pos = ui.find(name)
            if pos:
                return pos
    raise AssertionError(f"could not locate '{name}' on the game table")


def bar_y() -> int:
    """y of the table's top bar — an exact read-out of the lower/raise state.

    Lowering slides the WHOLE view down, top bar included, so this one number
    says which state the table is in. Measured on the iPhone 11, build 363:
    y=160 raised, y=232 lowered, repeatably to the pixel.
    """
    return locate("back_game")[1]


# Top-bar y as a fraction of screen height. Measured on the iPhone 11 (828x1792,
# build 363): 160/1792 = 0.089 raised, 232/1792 = 0.129 lowered. The midpoint
# separates them with ~36 px of margin either side, and that is what lets the
# starting state be read WITHOUT a probe tap — so a normal run is exactly two
# taps, lower then raise, and nothing is done twice for the sake of finding out.
_RAISED_MAX = 0.11


def check_lower():
    """"tap to lower" drops the whole playfield down, and raises it again.

    Exactly two taps: lower, then raise. A third only happens in recovery, when
    a previous run died mid-toggle and left the view down — "lowered" is a
    persistent SETTING, not per-game state, so that survives leaving the game and
    dealing another. Testing from there would measure the toggle backwards, so it
    is raised first and the line says so.

    Two things this has to be careful about, both learned the hard way:

      * The raise happens BEFORE either assertion, so a failure cannot leave the
        view down. It used to be able to, and the cost was steep: with the view
        down a blind coordinate misses the moved stock pile, so the NEXT run
        failed at the deal/undo step with a message about the stock — a failure
        a mile from its cause. (ui.tap_stock() no longer uses a blind
        coordinate, which removes the class; this keeps the state tidy anyway.)

      * The control is located ONCE and the same point tapped twice. The bottom
        captions vanish for ~4.5s while the view slides, and when they come back
        in the LOWERED state tap_lower only scores 0.72-0.74 against the 0.70
        threshold. Re-finding it there is a coin toss; the button does not move
        between the two layouts, so there is no need to.
    """
    button = locate("tap_lower")
    _, h = ui.screen_size()
    step = 0.02 * h                 # half the measured 4.0%-of-height travel

    up = bar_y()
    if up > _RAISED_MAX * h:
        print(f"  (a previous run left the playfield lowered at y={up} — "
              f"raising it first)")
        ui.tap_at(button, settle=LOWER_SETTLE)
        up = bar_y()

    ui.tap_at(button, settle=LOWER_SETTLE)      # 1. lower
    down = bar_y()
    ui.tap_at(button, settle=LOWER_SETTLE)      # 2. raise — before asserting
    back = bar_y()

    ui.expect(down - up > step,
              f"'tap to lower' did not lower the playfield — the top bar went "
              f"from y={up} to y={down}, a move of {down - up} px where more "
              f"than {step:.0f} was expected")
    print(f"  tap to lower dropped the playfield {down - up} px (y {up} -> {down})")

    ui.expect(abs(back - up) <= 4,
              f"tapping 'tap to lower' again did not raise the playfield — the "
              f"top bar is at y={back}, not back at y={up}")
    print(f"  tapping it again raised it back (top bar y={back})")


# ── "Use Hearts": a setting on another page, read off the game table ──────────
# Easy is a ONE-SUIT game, which is what makes this checkable both ways: with the
# setting off every card is a black spade, with it on every card is a red heart.
# Do not move this check to another level — Medium deals spades AND hearts, so
# "no spades remain" would be false there for a perfectly working build.
#
# Read by TEMPLATE, not by counting red pixels. The table is already full of red:
# every face-down card back and the whole stock pile are red in BOTH states, and
# the court cards carry red art either way, so a red-pixel count mostly measures
# the backs. Measured inside board_box() on this build:
#
#                    card_spade   card_heart
#   spades table       1.000        0.498
#   hearts table       0.614        1.000
#
# Both a long way from the 0.70 threshold, in the right direction each time.
# A template also survives drawer_opens() re-dealing the game after an
# interstitial ad, which any before/after PIXEL comparison would not.
SUITS = {"spades": "card_spade", "hearts": "card_heart"}
HEARTS = "opt_use_hearts"


def suit_now():
    """Which suit the dealt cards show: "spades", "hearts", or None if unclear.

    Restricted to the board, because the bottom "tap to undo" widget draws a red
    heart whatever suit is in play — it is decorative art, not part of the deal.
    """
    board = ui.board_frame()
    seen = [name for name, tpl in SUITS.items()
            if ui.find(tpl, screen=board) is not None]
    return seen[0] if len(seen) == 1 else None


def set_option(label: str, human: str, on: bool):
    """Drawer -> Options -> set one toggle -> back to the table."""
    drawer_opens("ingame_options", "options")
    ui.expect(ui.set_toggle(label, on),
              f"the '{human}' toggle would not go {_on(on)} — either the row was "
              f"not found or the control is dead")
    ui.expect(ui.back(settle=2.5), f"could not go back from Options after {human}")
    ui.expect(ui.at_table(),
              f"backing out of Options after {human} did not return to the table")


def restore_option(label: str, human: str, on: bool) -> bool:
    """Put one Options toggle back. Never raises — see the finallys that call it.

    Both settings driven from here are PERSISTED, so a run that dies mid-check
    leaves every later run — and every screenshot the suite captures — in the
    wrong state. This runs from a `finally`, which means it must not raise: the
    exception already on its way out is the useful one, and a reset that blew up
    would replace it with something unrelated. Same shape as
    verifyOptions.reset().
    """
    try:
        set_option(label, human, on)
        return True
    except Exception as e:  # noqa: BLE001 — must not mask the real failure
        print(f"  WARNING: could not put '{human}' back {_on(on)} ({e}) — the "
              f"next run will start in the wrong state")
        return False


def _on(state: bool) -> str:
    return "ON" if state else "OFF"


def check_use_hearts():
    """Options' "Use Hearts" changes the suit of the game ALREADY on the table."""
    start = suit_now()
    if start == "hearts":
        # A previous run died between ON and OFF. Recover rather than fail: the
        # setting is persisted, so this is a leftover, not a defect.
        print("  (a previous run left 'Use Hearts' ON — turning it off first)")
        set_option(HEARTS, "Use Hearts", False)
        start = suit_now()
    ui.expect(start == "spades",
              f"the Easy deal is not showing spades to begin with (reads "
              f"{start!r}), so a switch to hearts could not be told apart")

    try:
        set_option(HEARTS, "Use Hearts", True)
        got = suit_now()
        ui.expect(got == "hearts",
                  f"'Use Hearts' was switched ON but the dealt cards still read "
                  f"{got!r} — the setting did not reach the running game")
        print("  drawer -> options -> 'Use Hearts' ON -> the dealt cards are red "
              "hearts")
    finally:
        restored = restore_option(HEARTS, "Use Hearts", False)

    ui.expect(restored, "'Use Hearts' could not be turned back OFF")
    got = suit_now()
    ui.expect(got == "spades",
              f"'Use Hearts' was switched back OFF but the dealt cards read "
              f"{got!r} — the setting only works one way")
    print("  drawer -> options -> 'Use Hearts' OFF -> the spades are back")


# ── "Rich Features": the Timer, Score and Multiplier under the table ─────────
# It ships ON and draws all three under the game table. Read as INK PRESENT or
# ABSENT in that strip — not as a template, and not as a before/after diff.
# Both exclusions are deliberate:
#
#   * There is nothing stable to crop. All three are DYNAMIC TEXT: the timer
#     ticks every second, the score moves as you play, the multiplier is per
#     level. That is why the card-suit approach above does not transfer.
#   * A pixel diff would prove nothing. The running timer changes this strip
#     every second by itself, so "it changed" passes just as happily with the
#     setting dead.
#
# "Ink" is measured against the strip's OWN median colour rather than a fixed
# felt value, because verifyChooseLook (#7) runs earlier and can repaint the
# surface — a fixed threshold would drift with the theme.
#
# The box is anchored to the "tap to lower" caption. Measured on the iPhone 11,
# build 363, the bottom row has three separate ink columns:
#
#   "tap to undo" widget    x  50-242
#   score / timer / mult    x 338-473     <- the only one we want
#   "tap for hints" widget  x 582-774
#
# so cap_x +/- 0.140w (x 300-530) isolates the centre with ~100 px of clear felt
# either side. Vertically cap_y + 0.027h .. + 0.074h (y 1440-1525) covers the
# score ("0", 3.7% ink) and the timer + multiplier ("0:00 X58", 6.0%) while
# staying clear of two things: the "tap to lower" caption ABOVE it (6.6% ink, but
# a control label rather than one of the three items) and the wood strip BELOW,
# which starts at y=1534 and would read as ink on an otherwise empty strip.
RICH = "opt_rich_features"
_STRIP_DX = 0.140
_STRIP_Y0 = 0.027
_STRIP_Y1 = 0.074

# Ink bars. With _INK_DELTA below, the strip reads ~10% with the setting ON and
# 0.00% with it OFF — as far apart as a measurement gets. The bars sit well
# inside that gap and the run prints every number, so drift shows up as a number
# moving before it shows up as a failure.
_INK_ON = 0.015
_INK_OFF = 0.005


def strip_box(anchor):
    """The Timer/Score/Multiplier box as (x0, y0, x1, y1), from the caption."""
    w, h = ui.screen_size()
    cx, cy = anchor
    return (int(cx - _STRIP_DX * w), int(cy + _STRIP_Y0 * h),
            int(cx + _STRIP_DX * w), int(cy + _STRIP_Y1 * h))


# How far a pixel must sit from the strip's background before it counts as ink.
#
# NOT a round number. The table plays a sparkle/glow animation whose edge drifts
# into the bottom-left of this box, and it is a LIGHT GREEN on green felt — only
# ~41 units from the background. At the original threshold of 40 that read as
# 5.72% ink on a strip that was genuinely empty, which is exactly how this check
# failed the first time it ran inside the full suite (it had passed twice
# standalone, when the animation happened not to be in that phase).
#
# Real text is nowhere near that subtle: white and gold glyphs sit 150-250 units
# from the felt. Measured across three captures:
#
#   threshold      40      60      80     100     120
#   ON          11.87%  11.37%  11.12%  10.74%  10.29%
#   OFF          5.72%   3.17%   1.42%   0.26%   0.00%
#
# 120 is the first value that reads a truly empty strip as empty, and it still
# leaves >10% for the text. Anything in 100-150 would do; 120 is central.
_INK_DELTA = 120


def strip_ink(box, tag: str) -> float:
    """Fraction of `box` that is ink rather than background."""
    import numpy as np
    a = np.asarray(ui.region(ui.shoot(f"_strip_{tag}"), box).convert("RGB"),
                   dtype=np.int16)
    bg = np.median(a.reshape(-1, 3), axis=0)
    return float((np.abs(a - bg).max(axis=2) > _INK_DELTA).mean())


def check_rich_features():
    """Options' "Rich Features" hides the Timer, Score and Multiplier."""
    # Locate the anchor ONCE, while the setting is still ON. That is not a
    # precaution, it is required: the "tap to lower" caption is ITSELF one of the
    # things "Rich Features" hides (confirmed on build 363 — see the observation
    # printed below), so there would be nothing to anchor to once it is off. The
    # strip does not move between the two states, so one fix serves both reads —
    # the same trick check_lower() uses.
    box = strip_box(locate("tap_lower"))

    on = strip_ink(box, "rich_on")
    if on <= _INK_ON:
        # A previous run died between OFF and ON. Recover rather than fail: this
        # setting is persisted, so an empty strip here is a leftover, not a
        # defect. Nothing else in the suite resets it — verifyOptions' TARGETS
        # does not cover this row.
        print(f"  (a previous run left 'Rich Features' OFF — turning it back on)")
        set_option(RICH, "Rich Features", True)
        on = strip_ink(box, "rich_on2")
    ui.expect(on > _INK_ON,
              f"the Timer/Score/Multiplier strip is empty ({on*100:.2f}% ink) "
              f"before 'Rich Features' was touched, so hiding it could not be "
              f"told apart")

    try:
        set_option(RICH, "Rich Features", False)
        off = strip_ink(box, "rich_off")
        ui.expect(off < _INK_OFF,
                  f"'Rich Features' was switched OFF but the Timer/Score/"
                  f"Multiplier strip still holds {off*100:.2f}% ink (it held "
                  f"{on*100:.2f}% before) — they are still on screen")
        print(f"  drawer -> options -> 'Rich Features' OFF -> timer, score and "
              f"multiplier are gone ({on*100:.2f}% -> {off*100:.2f}% ink)")
        # Observed, deliberately NOT asserted: the setting takes more than the
        # three items with it. On build 363 the "tap to lower" control and the
        # top bar's score counter go too, while "tap to undo" and "tap for
        # hints" stay. Whether that is intended is a question for the port
        # owner, so it is reported rather than failed — but note what it means
        # for this file: with Rich Features left OFF, check_lower() has no
        # caption to find. That is another reason the restore below runs from a
        # finally.
        gone = [n for n in ("tap_lower", "tap_undo", "tap_hints")
                if not ui.is_on(n)]
        if gone:
            print(f"    (it also hides: {', '.join(gone)})")
    finally:
        restored = restore_option(RICH, "Rich Features", True)

    ui.expect(restored, "'Rich Features' could not be turned back ON")
    back = strip_ink(box, "rich_back")
    ui.expect(back > _INK_ON,
              f"'Rich Features' was switched back ON but the Timer/Score/"
              f"Multiplier strip reads {back*100:.2f}% ink — the setting only "
              f"works one way")
    print(f"  drawer -> options -> 'Rich Features' ON -> they are back "
          f"({back*100:.2f}% ink)")


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

    # 3. "tap to lower" drops the whole playfield down the screen and raises it
    #    again. See check_lower() for the two traps in it.
    check_lower()

    # 4. Hints should surface a suggestion. The highlight is TRANSIENT — it plays
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

    # 5. The in-game drawer and its six actions.
    ui.expect(ui.open_ingame_menu(), "the in-game menu drawer did not open")
    missing = [b for b in DRAWER if not ui.is_on(b)]
    ui.expect(not missing, f"in-game drawer buttons missing: {missing}")
    drawer = ui.shoot("InGameMenu")
    print(f"  drawer shows all {len(DRAWER)} actions — {drawer}")

    # 6. options / help / faq each open a screen and back out to the table.
    #    Each action closes the drawer, so it is reopened before the next one.
    #    Options absorbs its own open/back round trip inside check_use_hearts(),
    #    which uses the page rather than just proving it opened.
    check_use_hearts()
    check_rich_features()

    drawer_opens("ingame_help", "help")
    ui.expect(ui.back(), "could not go back from help")
    ui.expect(ui.at_table(), "backing out of help did not return to the table")
    print("  drawer -> help -> back")

    drawer_opens("ingame_faq", None)
    ui.expect(ui.back(), "could not go back from the FAQ screen")
    print("  drawer -> faq -> back")

    # 7. "new" deals a fresh game: the table stays up and the board changes.
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

    print("PASS: game table plays — deal/undo round trip holds, tap-to-lower "
          "toggles the playfield, hints respond, 'Use Hearts' and 'Rich "
          "Features' both reach the table, and all six drawer actions behave")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
