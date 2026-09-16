#!/usr/bin/env python3
"""Test: Choose Look applies a surface and a card back, all the way to the table.

Beyond opening the modal, this exercises what it's FOR. It picks the **6th**
Surface palette and the **5th** Cards palette, then opens a game and proves both
reached the thing the player actually looks at: the felt on the game table and
the backs of the cards. Picking a look that only repaints the modal would pass
every check inside the modal and fail here, which is the point.

The modal is also the one place where "the menu is visible" and "we are on the
menu" diverge — it overlays the menu, leaving the menu labels matchable behind
it (scripts/verify_unity_assets.py flagged this). ui.on_menu() rules the modal
out explicitly, and the close step below relies on that being correct.

NOT in tests/run_all.py: the look is saved by the app, so a test that repaints
the table has no business sitting in the middle of a suite that reads the table.
Run it on its own, or last, after everything else has already run.

IT STARTS OFFLINE AND FROM A KILL. A leftover online session (ads) can fire an
interstitial when this later deals Easy, so it enables Airplane Mode and turns
Wi-Fi off first, then Homes and terminates the way verifyRelaunch does, then
force-launches to the menu. That is before any look check, not between them.

IT PUTS THE DEFAULT LOOK BACK before it finishes, from a block that runs even
when the checks fail — and that is not tidiness. The menu's three ICON controls
carry the felt inside their crops, so on the tan surface this test applies they
score 0.692 (choose_look), 0.659 (more_games) and 0.619 (menu_logo) against a
0.70 bar. Leaving the new look on therefore breaks verifyMainMenu,
verifySpiderLogo and verifyMoreGamesBtn, and broke this test's OWN second run,
which could no longer find the control that opens its own modal. That is
measured, not predicted: it is how the second run actually failed.

The proof happens BEFORE the restore, on the table, so nothing is given up.

THERE IS NO "THE SCREEN CHANGED" ASSERTION, on purpose. Tapping an
already-selected palette is a legitimate no-op, and the selection persists
between runs — so a test that always taps the same palette passes once and then
fails forever after. That is not hypothetical: it is what the previous version
of this test did, and it is why it used to try three swatches until one moved.
The restore normally means the next run does start from the default, but a run
that dies before the restore leaves the new look on, and this test must survive
being run again after that.
Asserting the END STATE instead is both idempotent and a stronger claim, because
it is what "the new look is showing" actually means. Step 5 still PRINTS whether
the surface changed or was already applied, so a run says which case it was
without betting a pass on it.

Captures log/choose_look_surface.png, log/choose_look_cards.png and
log/choose_look_table.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyChooseLook.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402
from tests.verifyRelaunch import kill  # noqa: E402

SURFACE_N = 6       # reading order: row 2, column 3 — the light checkered wood
CARDS_N = 5         # reading order: row 2, column 2 — the black filigree deck

# WHAT THIS CANNOT TELL APART. Surface palettes 3, 6 and 9 are one cream/tan
# family that differ by PATTERN, not by colour — measured against a real capture
# of the table wearing palette 6, palette 3 scores 0.024 where 6 scores 0.011,
# both inside the bar. So the surface check proves "the table is wearing the tan
# palette", not "specifically the sixth of the three tan ones". Every other
# palette is rejected by a wide margin (0.073 upwards), and the card decks have
# no such pair — deck 5 wins by 5x over its nearest rival.
#
# Telling 3 from 6 would mean reading the PATTERN rather than the colour, and
# the pattern is what changes scale between the thumbnail and the table. It is
# not worth the fragility for the question being asked here.

SURFACE_COUNT = 9   # the Surface tab's grid is 3 x 3
CARDS_COUNT = 6     # the Cards tab's grid is 2 x 3

# How far the table may sit from the palette that was chosen. The target is NOT
# a constant: it is read off the swatch that was just tapped, in the same run,
# because this modal is the thing that repaints the felt and the suite's standing
# rule is never to threshold against a fixed felt colour (see verifyGamePlay's
# strip_ink and unity_ui's card_dialog).
#
# The comparison is on NORMALISED colour — each colour divided by its own total,
# so what is compared is the hue and not the brightness. That is not tidiness, it
# is the only thing that works for the CARDS: a palette thumbnail and a full-size
# card back are the same artwork at different scales, and the black deck is black
# line-work on a white field, so the thumbnail packs far more black per pixel
# than the real card does. Its raw colour reads [123 123 123] in the dialog and
# [143 151 156] on the table — 81 apart, enough to fail a passing app — while the
# two are within 0.032 of each other once brightness is divided out. Matching the
# artwork by correlation was tried and is useless here: the chosen deck scored
# 0.448 against 0.433 for a deck that is not even the same colour.
#
# Measured on the iPhone 11, build 363, against a real capture of the table
# after choosing palette 6 and deck 5 — every palette scored, not just the two:
#
#     felt  vs palette 6   0.011   next  0.024 (#3)   then 0.073, 0.224 .. 0.832
#     backs vs deck 5      0.022   next  0.106 (#2)   then 0.136, 0.152, 0.335
#
# The chosen one wins both, and the felt sits 0.832 from the teal it replaced.
# 0.06 clears both readings with room and still rejects every deck but the right
# one. It does NOT reject surface 3 — see "what this cannot tell apart" below.
TOL = 0.06

# A band of felt reads sd 4-5 per channel. Anything much above that has cards in
# it and is not felt, so it is not a reading to trust.
FLAT = 25

# Candidate felt bands, top of the band as a fraction of screen height, tried in
# order. More than one because a resumed game can carry longer columns than a
# fresh deal, and averaging a column in as "felt" would be a wrong number rather
# than a miss.
FELT_BANDS = (0.50, 0.58, 0.44, 0.64)
FELT_H = 0.06           # how tall each band is
FELT_X = (0.15, 0.85)   # trimmed either side, clear of the undo/hints widgets


def run():
    ui.expect(ui.offline(),
              "could not enable Airplane Mode / turn Wi-Fi off — Choose Look "
              "deals a game, and a leftover online session can fire an ad")
    ui.expect(ui.home(),
              "the Home press did not send the app to the background — "
              "without it a kill measures the harness, not the app")
    kill()
    ui.expect(ui.launch_to_menu(force=True), "could not reach the main menu")
    before = menu_felt()

    # 1. Open the modal. It reopens on whichever tab was last used, so normalise
    #    to Surface rather than assuming.
    ui.expect(ui.open_choose_look(),
              "the Choose Look modal did not open (no close button)")
    if not ui.is_on("screen_surface"):
        ui.expect(ui.tap("look_surface_tab", settle=2.0), "Surface tab not found")
    ui.expect(ui.at_screen("surface"),
              "the Surface tab content ('Simulate Depth') is not showing")
    shot_s = ui.shoot("choose_look_surface")

    # 2. The menu must NOT count as reachable while the modal covers it.
    ui.expect(not ui.on_menu(timeout=1.0),
              "on_menu() returned True while the Choose Look modal was open — "
              "the modal leaves the menu labels visible behind it")

    # 3. Both tabs open, and the Surface tab comes back.
    ui.expect(ui.tap("look_cards_tab", settle=2.5), "Cards tab not found")
    ui.expect(ui.at_screen("cards"),
              "the Cards tab content ('Extra Large Card-Symbols') is not showing")
    shot_c = ui.shoot("choose_look_cards")

    ui.expect(ui.tap("look_surface_tab", settle=2.5),
              "Surface tab not found on the way back")
    ui.expect(ui.at_screen("surface"), "could not switch back to the Surface tab")

    ok = False
    try:
        ok = check(before)
    finally:
        restored = restore()

    # Only reached when the checks passed — if one raised, that exception is
    # already on its way out and restore()'s warning stands on its own rather
    # than replacing the real failure.
    ui.expect(restored, "the default look could not be put back, so the app is "
                        "left on the new one — the menu's icon controls will not "
                        "match until it is changed back by hand")
    ui.expect(ok, "the Choose Look checks did not complete")

    ui.expect(ui.to_menu(), "could not return to the main menu at the end")
    print(f"PASS: Choose Look — Surface ({shot_s}) / Cards ({shot_c}) tabs switch, "
          f"palette {SURFACE_N} and deck {CARDS_N} apply, BOTH show on the game "
          f"table, and the default look is back")


def check(before):
    """Pick the two palettes and prove both reached the table. Returns True."""
    # 4. Choose the two palettes, keeping the colour of each.
    surface = pick("Surface", SURFACE_N, SURFACE_COUNT)
    ui.expect(ui.tap("look_cards_tab", settle=2.5),
              "Cards tab not found when going back for the card backs")
    ui.expect(ui.at_screen("cards"), "the Cards tab did not open the second time")
    cards = pick("Cards", CARDS_N, CARDS_COUNT)

    # 5. Close via the x (the modal has no back button) and land on the menu.
    ui.expect(ui.tap("look_close", settle=2.0), "modal close (x) not found")
    ui.expect(ui.on_menu(timeout=6.0),
              "closing the Choose Look modal did not return to the main menu")
    after = menu_felt()
    if before is not None and after is not None:
        moved = dist(before, after)
        print(f"  the menu surface {'changed' if moved > TOL else 'was already this palette'} "
              f"({moved:.3f} apart)")

    # 6. The real claim: both looks reached the game table.
    # Always deal Easy. Do not Resume a paused game, and do not use
    # start_game() — that calls settle_prompts(), which treats the Unity
    # abandon card as a tip and taps the left pill (No). Yes is on the right.
    ui.expect(ui.open_picker(),
              "could not open the difficulty picker to check the new look")
    ui.expect(ui.tap("difficulty_easy", settle=2.5),
              "the picker has no Easy row to tap")
    if ui.card_up(timeout=2.0):
        ui.expect(ui.answer_card(1, settle=3.0),
                  "could not tap Yes on the abandon confirmation")
        ui.expect(card_gone(timeout=4.0),
                  "Yes did not dismiss the abandon confirmation")
    elif ui.dialog_up(timeout=1.0):
        ui.expect(ui.answer_dialog(True),
                  "could not tap Yes on the abandon confirmation")
    # A new deal can raise the "Did you know?" tip. Leftmost is OK. Do this
    # only after the abandon card is gone, or we would tap No on that card.
    if ui.card_up(timeout=3.0):
        ui.answer_card(0, settle=1.5)
    # tap_undo is white text on the felt, so it misses on Surface 6. The
    # in-game menu still matches (~0.79 on tan), and a felt band is the
    # same reading the colour check uses.
    ui.expect(on_painted_table(timeout=12.0),
              "Easy did not deal a game after Yes on the confirmation")
    shot_t = ui.shoot("choose_look_table")

    felt = felt_colour()
    ui.expect(felt is not None,
              f"could not find a clear patch of felt on the table to read — every "
              f"candidate band had cards in it (see {shot_t})")
    gap = dist(felt, surface)
    ui.expect(gap <= TOL,
              f"the table's felt reads {bgr(felt)} but Surface palette "
              f"{SURFACE_N} is {bgr(surface)} — {gap:.3f} apart against a bar of "
              f"{TOL}. The chosen surface did not reach the game table (see "
              f"{shot_t})")
    print(f"  the table's felt matches Surface palette {SURFACE_N} "
          f"({bgr(felt)} vs {bgr(surface)}, {gap:.3f} apart)")

    backs = back_colour()
    ui.expect(backs is not None,
              f"could not find the card backs in the 'tap for hints' widget "
              f"(see {shot_t})")
    gap = dist(backs, cards)
    ui.expect(gap <= TOL,
              f"the card backs read {bgr(backs)} but Cards palette {CARDS_N} is "
              f"{bgr(cards)} — {gap:.3f} apart against a bar of {TOL}. The chosen "
              f"card back did not reach the game table (see {shot_t})")
    print(f"  the table's card backs match Cards palette {CARDS_N} "
          f"({bgr(backs)} vs {bgr(cards)}, {gap:.3f} apart)")

    return True


def restore(surface_n: int = 1, cards_n: int = 1) -> bool:
    """Put the DEFAULT look back. Never raises — it runs from a finally.

    This is not tidiness. The menu's three ICON controls carry the felt in their
    crops, and on the tan surface this test applies they score 0.692
    (choose_look), 0.659 (more_games) and 0.619 (menu_logo) against a 0.70 bar —
    so leaving the new look on breaks verifyMainMenu, verifySpiderLogo,
    verifyMoreGamesBtn, and this test's own next run, which could no longer open
    its own modal. Measured, not predicted: that is exactly how the second run
    failed.

    ui.open_choose_look() is what makes the restore possible at all, since the
    control it has to press is one of the three the new surface breaks.
    """
    try:
        if not ui.to_menu():
            print("  WARNING: could not reach the menu to put the default look back")
            return False
        if not ui.open_choose_look():
            print("  WARNING: could not reopen Choose Look to put the default back")
            return False
        for tab, tab_tpl, screen, n in (("Surface", "look_surface_tab", "surface", surface_n),
                                        ("Cards", "look_cards_tab", "cards", cards_n)):
            if not (ui.tap(tab_tpl, settle=2.5) and ui.at_screen(screen, timeout=6.0)):
                print(f"  WARNING: could not open the {tab} tab to restore it")
                return False
            if ui.look_pick(n) is None:
                print(f"  WARNING: could not select {tab} palette {n}")
                return False
        ui.tap("look_close", settle=2.0)
        if not ui.on_menu(timeout=6.0):
            print("  WARNING: the modal would not close after restoring the look")
            return False
        print(f"  put the default look back (Surface {surface_n}, Cards {cards_n})")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  WARNING: could not put the default look back ({e})")
        return False


def pick(tab: str, n: int, count: int):
    """Tap the nth palette of the open tab. Returns its colour.

    The count is asserted first: a grid that comes back the wrong size means the
    detector found something that is not a palette (or missed one), and an index
    into that is a tap at a coordinate nobody chose.
    """
    boxes = ui.look_swatches()
    ui.expect(len(boxes) == count,
              f"the {tab} tab shows {len(boxes)} palettes, expected {count} — "
              f"either the grid changed or something else on the modal is being "
              f"read as a palette, so palette {n} cannot be trusted")
    colour = ui.look_pick(n)
    ui.expect(colour is not None, f"could not tap palette {n} of the {tab} tab")
    print(f"  {tab}: chose palette {n} of {count} — {bgr(colour)}")
    return colour


def menu_felt():
    """The surface colour as the MAIN MENU shows it, or None.

    The menu is drawn on the same surface as the table, so this is a free
    "before" reading — no game needed. Only ever printed, never asserted.
    """
    img = ui._screen_image()
    h, w = img.shape[:2]
    return flat_patch(img, int(h * 0.62), int(h * 0.68), int(w * 0.05), int(w * 0.30))


def card_gone(timeout: float = 4.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not ui.card_up(timeout=0.2):
            return True
        ui.sleep(0.2)
    return False


def on_painted_table(timeout: float = 12.0) -> bool:
    """True on the table even when tap_undo cannot match the new felt."""
    deadline = time.time() + timeout
    while True:
        if ui.menu_button_pos() is not None or felt_colour() is not None:
            return True
        if time.time() >= deadline:
            return False
        ui.sleep(0.3)


def felt_colour():
    """The felt colour on the game table, from the first band that is really felt."""
    img = ui._screen_image()
    h, w = img.shape[:2]
    x0, x1 = int(w * FELT_X[0]), int(w * FELT_X[1])
    for top in FELT_BANDS:
        got = flat_patch(img, int(h * top), int(h * (top + FELT_H)), x0, x1)
        if got is not None:
            return got
    return None


def back_colour():
    """The card-back colour, read off the 'tap for hints' widget.

    NOT the stock pile: that empties as a game is played out, so the patch
    would be felt rather than a card. The hints widget always draws three
    full card backs. Anchored to the caption plus the offset
    tap_table_control() already uses for this control.
    """
    img = ui._screen_image()
    h, w = img.shape[:2]
    cap = ui.find("tap_hints", screen=img)
    if cap is None:
        cap = ui.find("tap_hints", threshold=0.55, screen=img)
    if cap is None:
        menu = ui.menu_button_pos()
        if menu is None:
            return None
        # hints sits bottom-right, same side as the top-bar menu
        cap = (menu[0], int(0.90 * h))
    cx = cap[0]
    cy = cap[1] + int(ui._CONTROL_DY["hints"] * h)
    return patch(img, cy - 30, cy + 30, cx - 45, cx + 45)


def flat_patch(img, y0, y1, x0, x1):
    """Mean colour of a region, but only if it is uniform enough to trust."""
    import numpy as np
    p = np.asarray(img[y0:y1, x0:x1], dtype=float).reshape(-1, 3)
    if p.size == 0 or p.std(axis=0).max() > FLAT:
        return None
    return p.mean(axis=0)


def patch(img, y0, y1, x0, x1):
    import numpy as np
    p = np.asarray(img[max(0, y0):y1, max(0, x0):x1], dtype=float).reshape(-1, 3)
    return None if p.size == 0 else p.mean(axis=0)


def dist(a, b) -> float:
    """How far apart two colours are once brightness is divided out.

    Each colour is scaled by its own total, so this compares the MIX of blue,
    green and red rather than how much light there is. See TOL for the
    measurement that made this necessary rather than merely neat.
    """
    sa, sb = float(sum(a)) or 1.0, float(sum(b)) or 1.0
    return float(sum(abs(float(x) / sa - float(y) / sb) for x, y in zip(a, b)))


def bgr(c) -> str:
    return "[" + " ".join(f"{int(round(v)):3d}" for v in c) + "]"


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
