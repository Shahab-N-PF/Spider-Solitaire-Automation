#!/usr/bin/env python3
"""Test: the "More Games" button opens the in-app cross-promo page. [UNITY]

"More Games" (gift icon, left of the main menu) opens FingerArts' in-app
cross-promo page ("Tap any game to download it!" over red curtains) — it stays
in the app rather than jumping to the App Store. Tapping a game there WOULD open
the App Store, so this only verifies the page opened (via its instruction text),
scrolls it, and walks back.

The page holds FIVE games but shows only three (Solitaire, Sudoku 2, Card Games
Platinum); FreeCell and Spiderette are below the fold, so a capture of the first
screenful silently misses two fifths of the curtain. ONE swipe is the whole
scroll — measured on an iPhone 11, build 363:

    swipe 1        content band moves 0.2672    FreeCell + Spiderette revealed
    swipes 2-10    content band moves 0.0027 - 0.0052   already at the bottom
    swipe 11       content band moves 0.0000

Those 0.003s are not scrolling: the promo tiles carry an animated smiley, so a
stationary page still flickers a few pixels between captures. That is exactly
why the bar is a MEASURED 0.05 and not "did anything change at all" — a
change-detector would call this page scrollable forever.

The header ("back" + the instruction line) is pinned — it moved 0.0000 through
every swipe — so the band excludes it rather than diluting the measurement with
an eighth of a screen that can never move.

Captures log/MoreGames.png (the top, which is the baselined screen) and
log/MoreGamesBottom.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyMoreGamesBtn.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

BAND = (0.12, 0.97)     # the promo list, below the pinned header
MOVED = 0.05            # the one real swipe moves 0.267; a spent one moves
                        # <= 0.005 (animated smileys), so this sits between them


def band(tag):
    """The scrolling promo list as an image, minus the pinned header."""
    w, h = ui.screen_size()
    return ui.region(ui.shoot(tag), (0, int(h * BAND[0]), w, int(h * BAND[1])))


def scroll_once():
    """One swipe, which is this page's entire scroll. Asserts it moved."""
    before = band("_mg_top")
    ui.scroll(down=True)
    moved = ui.diff_frac(before, band("_mg_end"))
    ui.expect(moved >= MOVED,
              f"the More Games page did not scroll — one swipe changed only "
              f"{moved:.1%} of the list (a real swipe changes 27%), so FreeCell "
              f"and Spiderette stay below the fold and cannot be tapped")
    ui.expect(ui.at_screen("more_games", timeout=4.0),
              "scrolling More Games navigated away from it instead of moving "
              "the promo list")
    bottom = ui.shoot("MoreGamesBottom")
    print(f"  the promo list scrolls — {moved:.1%} of it moved, revealing the "
          f"last two games, see {bottom}")


def run():
    shot = ui.visit_sub_screen("more_games", "more_games", "MoreGames",
                               after=scroll_once)
    print(f"PASS: More Games opened (verified 'Tap any game to download it!'), "
          f"scrolled to its last two games, and returned to the main menu "
          f"(see {shot})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
