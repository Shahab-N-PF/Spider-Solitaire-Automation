#!/usr/bin/env python3
"""Test: killing the app on the game screen brings the played game back. [UNITY]

The requirement, in full: kill the app while the GAME SCREEN is open, launch it
again, and it must come back ON THE GAME SCREEN — both when it is launched again
after ~3-4 seconds and when it is launched again after 30 seconds or more. Both
cases are run here, as two legs.

IT NEVER ABANDONS A GAME TO START ANOTHER. Leaving the table pauses the game
rather than ending it, and the picker then shows a red "Resume" ribbon, so a
run that follows another run always has a game waiting. ui.resume_or_deal()
carries on with the table if one is open, resumes from the picker if one is
paused, and deals only when there is genuinely nothing to come back to.

That also makes the second leg a slightly harder question than the first: the
board it kills is normally one that has already been through a kill once, so
the long-wait check is not just the short one repeated.

**One move is played before the kill.** A freshly dealt board is not proof of
anything: an app that threw the game away and dealt a brand new one would still
show ten columns of cards. So the leftmost card is tapped first, the board is
captured AFTER that move, and it is that played position the relaunch has to
reproduce. If the leftmost card has no legal move the rightmost is tried, and if
neither does, a row is dealt from the stock — all three are played actions that
have to survive a kill, and the run prints which one it used.

The board is compared by CORRELATION, not pixel for pixel (ui.board_score over
ui.board_box). Reading the screen is the only way to read game state here —
Unity publishes no accessibility tree — but the app does not redraw a restored
board identically, so subtracting the two frames answers the wrong question.
See SAME_GAME below for the measurement that settled it.

HOME IS PRESSED BEFORE THE KILL, and that is load-bearing. It is what a person
does — the app switcher backgrounds an app before you can swipe it away — and it
is also the only version of the kill that measures the app rather than the
harness. Measured here on build 363, with a game in progress and one move
played, at both gaps:

    move -> Home -> kill -> relaunch          the GAME SCREEN comes back
    move -> kill from the foreground          the MAIN MENU comes back

The app writes its state when it goes to the BACKGROUND, so a WDA terminate
straight from the foreground — which no user can perform — takes the game with
it. A run of this test WITHOUT the Home press failed both legs on the menu, and
that failure said nothing about the product. The same trap is recorded for
settings in the note above opt_top() in unity_ui.py.

THE RESTORED GAME COMES BACK PAUSED, behind a "tap a card to start" prompt.
That is still "came back on the game screen" — the board underneath is the
played one — but it is a real difference from where the app was killed, so
relaunch() reports it. Note the prompt means what it says: tapping the CAPTION
does not clear it, only tapping a card does, and tapping a card would move one.
So the board is compared with that text still on screen, which is one more
reason the comparison cannot be a per-pixel diff.

Leaves a game in progress on the table when it finishes, as verifyPlay does.

NOT in tests/run_all.py. It kills the app, which hides the Dev Panel button that
verifyVictory and verifyDifficultyLevels need, so there is no slot for it in the
suite that does not cost more than it is worth. Run it on its own.

Captures log/relaunch_quick.png and log/relaunch_long.png, each beside the
log/relaunch_<leg>_played.png the comparison is made against.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set, and the
device OFFLINE — online, a cross-promo interstitial can land on the relaunch and
be misread as a lost game.
Run:  ./.venv/bin/python tests/verifyRelaunch.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import helpers  # noqa: E402
import unity_ui as ui  # noqa: E402

# The two cases from the requirement. LONG_WAIT carries a small margin past the
# 30-second line so a second of timing slop cannot land it on the wrong side.
# tag, and how long to leave the app dead before launching it again.
#
# NEITHER leg deals if a game is already going: ui.resume_or_deal() carries on
# with the table, or resumes the paused game from the picker, and only deals
# when there is nothing to come back to. So the second leg normally kills a board
# that has already survived the first kill, which is a stronger claim than
# repeating the first check with a longer wait.
LEGS = (("quick", 3.5), ("long", 35.0))

# Fraction of the board that must change for a tap to count as a move. Guards
# against a tap that only SELECTS a card: a selection highlight is a small
# change and may not be part of saved state, so counting one as the move would
# produce a mismatch after the relaunch and blame the wrong thing.
#
# Measured on the iPhone 11, build 363: a real single-card move reads 1.59% and
# a moved run of cards 8.69%. One card covers ~0.92% of board_box() on this
# screen, so the 1% bar sits just above "one card lit up" and just below "one
# card went somewhere" — which is the line it has to draw.
MOVED = 0.01

# How well the restored board must match the one that was killed, as a
# TM_CCOEFF_NORMED correlation (1.0 is identical). Measured on build 363:
#
#     the same game, restored after a kill      0.950, 0.975
#     a DIFFERENT deal                          0.774, 0.791
#     the difficulty picker / the main menu     0.279, 0.276
#
# so 0.90 sits in open space between "my game came back" and "a game came back".
#
# This USED to be a per-pixel diff with a 1% bar, and that was the wrong tool.
# The app does not redraw a restored board identically — it came back one pixel
# over in one run and with visibly wider card spacing in another — so the pixel
# diff read 11.58% and 9.07% on boards whose cards were provably identical, and
# failed a passing app. Correlation with a scale sweep absorbs a redraw and
# still separates a different deal by a wide margin. See ui.board_score().
SAME_GAME = 0.90

# at_table() is one anchor (tap_undo). These are the five the table really
# carries, and the same set verifyGamePlay asserts.
CONTROLS = ("back_game", "in_game_menu", "tap_undo", "tap_lower", "tap_hints")


def run():
    failures = []
    for tag, wait in LEGS:
        try:
            leg(tag, wait)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL: {tag:5} — {e}")
            failures.append(f"{tag} ({e})")
    if failures:
        raise AssertionError(
            f"{len(failures)}/{len(LEGS)} relaunch case(s) failed: "
            + "; ".join(failures))
    print("PASS: the app was killed on the game screen and launched again after "
          f"{LEGS[0][1]:.0f}s and after {LEGS[1][1]:.0f}s — the same game came "
          "back both times, the second kill taken on a board that had already "
          "survived the first")


def leg(tag: str, wait: float):
    """One case: get a game, play a move, kill, wait, launch again, check."""
    print(f"  {tag}: {ui.resume_or_deal('easy')}")
    played, how, moved = play_one_move(tag)
    shot_played = ui.shoot(f"relaunch_{tag}_played")
    print(f"  {tag}: {how} ({moved * 100:.2f}% of the board) — {shot_played}")

    ui.expect(ui.home(), "the Home press did not send the app to the background — "
                         "without it this measures the harness, not the app")
    killed_at = kill()
    ui.sleep(wait)
    gap = time.monotonic() - killed_at
    relaunch()

    shot = ui.shoot(f"relaunch_{tag}")
    ui.expect(ui.in_app(),
              f"Spider is not the foreground app after the relaunch — "
              f"{ui.active_app() or 'WDA would not say which app is'} is ({shot})")
    ui.expect(ui.at_table(timeout=15.0), not_the_table(shot))
    missing = [n for n in CONTROLS if not ui.is_on(n)]
    ui.expect(not missing,
              f"the game screen came back but these controls are missing: "
              f"{', '.join(missing)} ({shot})")

    score = ui.board_score(played)
    ui.expect(score >= SAME_GAME,
              f"the app came back on a game screen, but the board only matches "
              f"the one that was killed at {score:.3f} (bar {SAME_GAME:.2f}) — "
              f"it restored A game, not the game that was being played. Compare "
              f"{shot_played} with {shot}")
    print(f"PASS: {tag:5} killed on the game screen, launched again {gap:.1f}s "
          f"later, and came back on the same board (match {score:.3f})")


def play_one_move(tag: str):
    """Play one card. Returns (settled board, what worked, how much it moved).

    Tries the leftmost card, then the rightmost, then the stock. A tapped card
    with no legal move leaves the board alone, and that is not a failure — it is
    a normal deal — so it falls through to the next option rather than raising.
    """
    before = ui.board_shot(f"relaunch_{tag}_move_before")
    for col, human in ((0, "tapping the leftmost card moved it"),
                       (9, "tapping the rightmost card moved it")):
        pos = ui.bottom_card(col)
        if pos is None:
            continue
        ui.tap_at(pos, settle=2.0)
        if ui.card_up(timeout=0.5):
            ui.answer_card(0)      # the "Did you know?" tip; leftmost is OK
        after = ui.board_shot(f"relaunch_{tag}_move_{col}")
        moved = ui.diff_frac(before, after)
        if moved >= MOVED:
            return settled(tag), human, moved
        before = after

    # Neither end had a legal move. Dealing a row always changes the board
    # (measured at 9.4% in verifyGamePlay) and is just as much a played action.
    ui.expect(ui.tap_stock(), "could not tap the stock pile")
    after = ui.board_shot(f"relaunch_{tag}_move_stock")
    moved = ui.diff_frac(before, after)
    ui.expect(moved >= MOVED,
              f"no move could be played before the kill — neither end card moved "
              f"and dealing from the stock changed only {moved * 100:.2f}% of the "
              f"board. This is a rig problem, not a restore problem: there is no "
              f"played state to check for")
    return settled(tag), "dealing a row from the stock changed the board", moved


# Two captures of a still board differ by less than this. Only ever compared
# WITHIN one session, where the geometry cannot move, so a plain pixel diff is
# the right tool here — unlike the across-a-relaunch comparison above.
STILL = 0.01


def settled(tag: str, tries: int = 3):
    """The board once it has stopped moving, as a BGR frame for board_score().

    A card move animates. Without this the state captured "at the moment of the
    kill" could be a half-drawn frame, which nothing could ever match — and the
    mismatch would be read as the app losing the game.
    """
    prev = ui.board_shot(f"relaunch_{tag}_settle0")
    for i in range(1, tries + 1):
        ui.sleep(1.5)
        now = ui.board_shot(f"relaunch_{tag}_settle{i}")
        if ui.diff_frac(prev, now) <= STILL:
            return ui.board_frame()
        prev = now
    print("    (the board was still moving when it was captured — a low score "
          "below may be the animation, not the restore)")
    return ui.board_frame()


def kill():
    """Terminate the backgrounded app. Returns when it is really gone.

    ui.terminate() swallows every error and returns None, so the only proof the
    app went is the foreground bundle id changing. Without this check the test
    could report a clean pass purely because nothing was ever killed.
    """
    # NOT helpers.launch_app() as a fallback: that would foreground the app
    # again and undo the Home press this is called after.
    sid = helpers.current_session()
    ui.expect(sid, "no WDA session to terminate through")
    ui.terminate(sid)
    for _ in range(24):
        if ui.active_app() != config.BUNDLE_ID:
            return time.monotonic()
        ui.sleep(0.25)
    raise AssertionError(
        "the app was still in the foreground 6s after being terminated — it was "
        "never killed, so nothing after this would mean anything")


def relaunch():
    """Launch again and clear only what is safe to clear.

    force=True because the app is confirmed dead by now: a plain attach could
    quietly find a live app and invalidate the whole measurement.

    NOT ui.settle_prompts() — that answers an abandon prompt with Yes, which
    would throw away the very game being checked. Only the recognised
    first-launch gates (which a kill is documented to bring back) and the tip
    card are touched.
    """
    ui.launch(force=True)
    ui.clear_overlays()
    if ui.card_up(timeout=0.5):
        ui.answer_card(0)
    if ui.have("tap_to_start") and ui.is_on("tap_to_start"):
        ui.tap("tap_to_start", settle=2.0)
        print("    (the restored game needed a 'tap to start' before it resumed)")


def not_the_table(shot: str) -> str:
    """Why the game screen is not showing — the four cases mean four things."""
    if ui.on_menu(timeout=1.0):
        return (f"the app came back on the MAIN MENU, not the game screen "
                f"({shot}) — the game in progress was not restored. The Home "
                f"press before the kill is asserted above, so the app did get "
                f"its moment to save: this is the product, not the harness")
    if ui.at_screen("difficulty", timeout=1.0):
        return (f"the app came back on the difficulty picker, not the game "
                f"screen — the game was dropped but not forgotten ({shot})")
    if ui.lost(timeout=1.0):
        return (f"nothing recognisable is on screen after the relaunch, so this "
                f"says nothing about the game: {ui.blocking()} ({shot})")
    return (f"the app came back, but the game screen's 'tap to undo' anchor is "
            f"not showing ({shot})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
