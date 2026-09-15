#!/usr/bin/env python3
"""Test: the promo-game icons on the home screen. [UNITY]

FingerArts shows a vertical strip of other-game icons on the left of the main
menu, above "More Games" (Solitaire, Sudoku 2, Card Games, FreeCell, Spiderette).
This asserts they are present.

THIS TEST NEEDS AT LEAST ONE COMPLETED GAME. The strip only appears once the
player has finished a game; with a fresh install and all stats at 0 the app does
not draw it at all. That is app behaviour, not a port bug and not a slow fetch.

Which is why this test is LAST in tests/run_all.py, after verifyVictory — that
test wins a game with the Dev Panel cheat, which satisfies the precondition.
Do not move it earlier in the list, and do not run it standalone on a
freshly-installed build without completing a game first.

Measured on one iPhone 11, build 353, no reinstall in between (peak
TM_CCOEFF_NORMED, >=0.7 matches):

    12:07  fresh install, 0 wins    0 of 5   0.305 - 0.641   strip absent
    12:11  after T&C, relaunch, 12s settle, More Games visited — still 0 wins
                                    0 of 5   0.343 - 0.433   still absent
    12:43  after verifyVictory completed a game
                                    4 of 5   0.867 - 0.924   strip drawn

The 5th icon, promo_freecell, misses at ~0.54 while plainly on screen: the
FreeCell app icon was REDESIGNED (lighter squircle with a sparkle) and
`assets/promo_freecell.png` still holds the old dark-blue square. That is a
stale template, not a missing icon. The same thing shows up as
promo_spiderette scoring 0.329 against the iPhone 14's build-343 capture.

What ruled out the alternatives:
  * Not a rendering/scale artifact — the other four Obj-C templates match
    Unity's own rendering at 0.867-0.945.
  * Not "no promo data" — More Games loaded its full curtain while the menu
    strip was still empty, so those two are fed separately.
  * Not a build regression. An earlier version of this file called the empty
    strip a build-353 regression. That was wrong: it was written from a
    fresh-install capture with zero completed games.

Why this matches against the Obj-C templates: the icons are largely the same
artwork, and the set was cut at this device's own resolution so scale is right.

Steps:
  1. every icon in the strip is present;
  2. each icon, tapped, HANDS OFF TO THE APP STORE — checked with the foreground
     app's bundle id (com.apple.AppStore), not by pixels, because no screenshot
     can tell you which app you are looking at;
  3. switching back returns to Spider's menu. Coming back uses ui.resume(),
     which foregrounds the app WITHOUT killing it, so nothing in the run is
     lost. Never terminate to get back;
  4. each icon opens the RIGHT game — checked by the App Store page's NAME,
     read from its accessibility tree (the store is an ordinary UIKit app, so
     unlike the game it publishes real text). The test brings the device
     online before opening the icons, so every destination must render and
     the name check cannot be skipped.

     This used to assert only that the five pages DIFFER from each other, which
     a swap survives — swap two links and you still have five different pages.
     The name check is in two halves, and the second is the one that matters:
     each page must carry its icon's expected name, AND each expected name must
     match exactly ONE of the five. Without that second half the first is weaker
     than it looks, because three of the five titles contain "Solitaire" and two
     contain "Card".

Captures log/more_games_icons.png and log/promo_store_<icon>.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyMoreGamesIcons.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import unity_ui as ui  # noqa: E402
from airtest.core.api import exists  # noqa: E402
from airtest.core.cv import Template  # noqa: E402

PROMO_ICONS = ("promo_solitaire", "promo_sudoku2", "promo_cardgames",
               "promo_freecell", "promo_spiderette")

STORE_BUNDLE = ui.APP_STORE             # where a working promo icon lands

# The App Store name each icon must land on, as a substring of the page title.
# Measured (titles as ui.store_title() cleans them):
#
#   promo_solitaire   Solitaire: Classic Cards
#   promo_sudoku2     Sudoku - Classic Brain Game
#   promo_cardgames   Card Games
#   promo_freecell    FreeCell Solitaire
#   promo_spiderette  Solitaire Spiderette
#
# These are SUBSTRINGS so a version suffix or a tagline change does not break
# them — but they are picked to be unique, and run() ASSERTS that uniqueness
# rather than trusting it. That matters more than it looks: three of the five
# titles contain "Solitaire" and two contain "Card", so an obvious keyword like
# "solitaire" would pass on the WRONG page. A check that looks strict and is not
# is worse than no check, because it reads as proof.
EXPECTED = {
    "promo_solitaire":  "Solitaire: Classic Cards",
    "promo_sudoku2":    "Sudoku",
    "promo_cardgames":  "Card Games",
    "promo_freecell":   "FreeCell",
    "promo_spiderette": "Spiderette",
}


def objc_template(name, threshold=0.7):
    """A template from the Obj-C set (see the module docstring for why)."""
    return Template(os.path.join(config.ASSETS, name + ".png"), threshold=threshold)


def art_variants(name):
    """Every known crop of one icon: `promo_x.png` and an optional `_alt`.

    These are OTHER APPS' icons, so their art changes on the publisher's
    schedule, not with this build — FreeCell's was redesigned from a dark blue
    square to a lighter squircle with a sparkle. Accepting any known variant
    means a third-party icon refresh does not read as "the strip is missing".
    Add a new `<name>_alt.png` (or bump the existing one) when art changes again.
    """
    return [n for n in (name, name + "_alt")
            if os.path.exists(os.path.join(config.ASSETS, n + ".png"))]


def icon_pos(name, timeout=6.0):
    """Where an icon is on screen, or None. Polls — the icons ANIMATE.

    A shine sweeps across the strip, and while it is over an icon the match
    score dips below threshold, so a single look can miss an icon that is
    plainly there (this is why the presence check above and the tap below can
    disagree about the same icon).
    """
    deadline = time.time() + timeout
    while True:
        for variant in art_variants(name):
            pos = exists(objc_template(variant))
            if pos:
                return pos
        if time.time() >= deadline:
            return None
        time.sleep(0.5)


def check_redirect(name):
    """Tap one icon, prove it hands off to the App Store, come back. Capture path.

    Coming back is ui.resume() — foreground Spider again WITHOUT killing it, so
    the run keeps whatever state it had. Never terminate here.
    """
    pos = icon_pos(name)
    ui.expect(pos, f"[{name}] the icon is on the menu but could not be located "
                   f"again to tap it")
    ui.tap_at(pos, settle=4.0)

    went_to = ui.left_app()
    ui.expect(went_to == STORE_BUNDLE,
              f"[{name}] tapping the icon did not open the App Store — the "
              f"foreground app is {went_to or 'unknown'}. A promo icon that goes "
              f"nowhere is a dead link.")
    shot = ui.shoot(f"promo_store_{name}")
    title = ui.store_title()            # read BEFORE leaving — it is per-page

    ui.expect(ui.resume(), f"[{name}] could not switch back to Spider from the "
                           f"App Store")
    ui.expect(ui.on_menu(timeout=10.0),
              f"[{name}] came back from the App Store but not to the main menu")
    return shot, title


def looks_the_same(a, b, tol=8.0):
    """True when two App Store captures are the same page.

    Compares ONLY the band holding the app icon and title, not the whole page.
    These are all the same publisher, so the pages share their layout and most
    of their pixels — whole-page comparison put FreeCell and Spiderette, two
    genuinely different games, just 3.55 apart, which is too close to "identical"
    to assert anything on. Restricted to the title band the same pair is 18.36,
    and the closest of all ten pairs is also 18.36, so tol=8 sits in open space:
    an identical page scores ~0, a different one at least twice the tolerance.

    The band is expressed as a fraction of height so it holds on other devices.
    """
    import cv2
    import numpy as np
    ia, ib = cv2.imread(a, 0), cv2.imread(b, 0)
    if ia is None or ib is None or ia.shape != ib.shape:
        return False
    top, bottom = int(ia.shape[0] * 0.11), int(ia.shape[0] * 0.28)
    band_a, band_b = ia[top:bottom], ib[top:bottom]
    return float(np.abs(band_a.astype("int16") - band_b.astype("int16")).mean()) < tol


def check_destinations(names, titles):
    """Assert each icon opened the page named for it. Raises on failure.

    A function rather than inline code so the SWAP case can be proved
    offline: hand it a titles dict with two entries exchanged and it must
    raise. A destination check that has never been shown to fail is not a
    check.
    """
    # The pages loaded, so WHICH page each icon opened is answerable — by
    # NAME, read out of the App Store's accessibility tree. "The five pages
    # differ from each other" (all this used to check) would still pass if
    # two links were SWAPPED, because a swap leaves five different pages.
    missing = [n for n in names if not titles[n]]
    ui.expect(not missing,
              f"the App Store page title could not be read for {missing}, so "
              f"which game those icons open is unverified. The store publishes "
              f"a real accessibility tree, so an empty title means the page "
              f"had not rendered — not that the link is wrong.")

    wrong = [(n, titles[n]) for n in names
             if EXPECTED[n].lower() not in titles[n].lower()]
    ui.expect(not wrong,
              "these promo icons opened the WRONG App Store page: " + "; ".join(
                  f"{n} opened {t!r} but should carry "
                  f"{EXPECTED[n]!r}" for n, t in wrong))

    # And each expected name must pick out exactly ONE of the five pages —
    # otherwise the check above could be satisfied by the wrong page. This is
    # the half that actually catches a swap.
    ambiguous = []
    for n in names:
        hits = [m for m in names if EXPECTED[n].lower() in titles[m].lower()]
        if hits != [n]:
            ambiguous.append((n, EXPECTED[n], hits))
    ui.expect(not ambiguous,
              "these expected names no longer identify one page each, so the "
              "destination check cannot be trusted and EXPECTED needs "
              "re-picking: " + "; ".join(
                  f"{e!r} (for {n}) matched {hits}" for n, e, hits in ambiguous))

    for n in names:
        print(f"    {n} -> {titles[n]}")
    print(f"  all {len(names)} icons open the RIGHT App Store page, by name")


def run():
    net = ui.online()
    ui.expect(bool(net),
              "could not leave Airplane Mode / join Wi-Fi — promo destinations "
              "need the App Store pages to load")
    print(f"  online on {net}")

    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.sleep(3)                     # the strip animates in after the menu settles

    present = [n for n in PROMO_ICONS
               if any(exists(objc_template(v)) for v in art_variants(n))]
    missing = [n for n in PROMO_ICONS if n not in present]
    shot = ui.shoot("more_games_icons")

    ui.expect(not missing,
              f"{len(missing)}/{len(PROMO_ICONS)} home-screen promo icons did not "
              f"match: {missing}. Before filing: the strip only appears once at "
              f"least ONE GAME HAS BEEN COMPLETED — on a fresh install with stats "
              f"at 0 it is not drawn at all. Complete a game (or run "
              f"tests/verifyVictory.py) and re-run. promo_freecell is also a known "
              f"STALE template — that icon was redesigned. See {shot}")
    print(f"  all {len(PROMO_ICONS)} promo icons present — see {shot}")

    # Every icon is a link: tap it, prove it hands off to the App Store, and come
    # back by switching apps (never by killing Spider).
    stores, titles = {}, {}
    for name in PROMO_ICONS:
        stores[name], titles[name] = check_redirect(name)
        print(f"  {name}: opens the App Store, and switching back returns to the menu")

    # The device was brought online above, so identical store captures mean the
    # pages failed to render. Do not silently downgrade that to an unverified
    # result: the destination assertions are required for this test.
    names = list(PROMO_ICONS)
    first = stores[names[0]]
    if all(looks_the_same(first, stores[n]) for n in names[1:]):
        ui.expect(False,
                  "the App Store pages all look identical after going online; "
                  "promo destinations were not rendered")
    else:
        check_destinations(names, titles)

    print(f"PASS: promo icons are present and every one opens the App Store — "
          f"see {shot}")


# Real titles as measured on the device (build 363), for the offline self-test.
MEASURED = {
    "promo_solitaire":  "Solitaire: Classic Cards",
    "promo_sudoku2":    "Sudoku - Classic Brain Game",
    "promo_cardgames":  "Card Games",
    "promo_freecell":   "FreeCell Solitaire",
    "promo_spiderette": "Solitaire Spiderette",
}


def selftest():
    """Prove check_destinations() actually FAILS on a swap. No device needed.

    A destination check that has never been seen to fail is not a check — and
    this one replaced a weaker test that looked strict, so the burden is real.
    Run:  ./.venv/bin/python tests/verifyMoreGamesIcons.py --selftest
    """
    names = list(PROMO_ICONS)
    bad = []

    def must(label, titles, catch):
        try:
            check_destinations(names, dict(titles))
            got = "passed"
        except AssertionError:
            got = "caught"
        ok = (got == "caught") == catch
        print(f"  {'ok ' if ok else 'BAD'} {label:34} {got}")
        if not ok:
            bad.append(label)

    must("the measured titles", MEASURED, catch=False)
    for a, b in (("promo_freecell", "promo_spiderette"),
                 ("promo_solitaire", "promo_cardgames")):
        t = dict(MEASURED)
        t[a], t[b] = MEASURED[b], MEASURED[a]
        must(f"swap {a.split('_')[1]}/{b.split('_')[1]}", t, catch=True)
    t = dict(MEASURED); t["promo_sudoku2"] = MEASURED["promo_solitaire"]
    must("two icons -> the same page", t, catch=True)
    t = dict(MEASURED); t["promo_freecell"] = ""
    must("a page that never rendered", t, catch=True)
    # A suffix rename is NOT a destination change, so it must still pass — the
    # expected names are substrings precisely so this does not cry wolf. A
    # rename that DROPS the name (Card Games -> Klondike Deluxe) does fail.
    t = dict(MEASURED); t["promo_cardgames"] = "Card Games Platinum Deluxe"
    must("a suffix rename", t, catch=False)
    t = dict(MEASURED); t["promo_cardgames"] = "Klondike Deluxe"
    must("a rename that drops the name", t, catch=True)

    print("SELFTEST FAIL: " + ", ".join(bad) if bad
          else "SELFTEST PASS: the destination check catches every swap")
    return not bad


if __name__ == "__main__":
    if "--selftest" in sys.argv:        # offline proof, no device
        sys.exit(0 if selftest() else 1)
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
