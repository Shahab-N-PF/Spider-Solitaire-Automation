#!/usr/bin/env python3
"""Compare the iPhone 14 Pro Max **Unity** build's screens against the iPhone 14
Pro Max **Obj-C** baselines (the iPhone-14 analog of tests/compare_unity_ip7.py).

Unlike the iPhone 7 (which can't run WDA and is captured via tidevice), the
iPhone 14 Pro Max runs WDA under Xcode 26.5, so both sets are captured over
**WDA + Airtest** (see iphone14/README.md):
  - Obj-C 7.42.5  -> iphone14/baselines/<name>.png   (the reference)
  - Unity 8.0.0   -> log/ip14_unity/<name>.png         (this run's captures)

This script exact-pixel diffs each Unity capture against its Obj-C baseline with
iPhone-14 (1290x2796) mask regions, subtracts any learned volatile-pixel mask
(iphone14/baselines/<name>.volatile.png, animated menu sparkle / smiley cursors),
writes log/diff_ip14_<name>.png (baseline | Unity with differing pixels in red +
boxed), and prints a per-screen diff% summary (ranked, worst first). `--report`
regenerates the versioned report via scripts/gen_versioned_report.py.

Run:
  ./.venv/bin/python tests/compare_unity_ip14.py            # diff + summary
  ./.venv/bin/python tests/compare_unity_ip14.py --report   # + HTML report
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import config  # noqa: E402
import visual  # noqa: E402

UNITY_DIR = os.path.join(config.LOG, "ip14_unity")               # Unity 8.0.0 captures
BASE_DIR = os.path.join(config.ROOT, "iphone14", "baselines")    # Obj-C 7.42.5

# iPhone 14 Pro Max = 1290x2796 portrait (19.5:9 — a taller aspect than the
# iPhone 7's 16:9, so these regions are measured off real 1290x2796 captures,
# NOT scaled from the iPhone-7 values). Volatile chrome to ignore everywhere:
W, H = 1290, 2796
STATUS_BAR = (0, 0, W, 115)          # iOS status bar / Dynamic Island (time, battery)
BOTTOM_BANNER = (0, 2420, W, H)      # rotating cross-promo house banner + wood tray
                                     # (starts below the victory buttons / undo pile)
COMMON_IGNORE = [STATUS_BAR, BOTTOM_BANNER]

GAME_TABLE_CARDS = (0, 560, W, 1180)  # the randomly-dealt tableau + foundations/stock on Play
INGAME_TABLE = (0, 560, W, 1180)      # dealt cards behind the in-game menu panel
# Victory screens show run-dependent won-count + score/time/moves/run numbers;
# mask the "won X" line + the current/rank/best block so the diff reflects layout.
VICTORY_STATS = (100, 1000, W - 100, 1770)
# Build 343 reintroduced a development-only "Dev Panel" button at the bottom-right
# of both victory screens (absent in build 341 — confirmed against pixels, not just
# the curated note). Masked by request so the diff reflects the rest of the layout;
# most of the button already falls under BOTTOM_BANNER, this also covers the top
# sliver that pokes above y=2420.
DEV_PANEL = (955, 2405, W, 2540)
# Statistics (scrolled to bottom) shows per-run values in a right-hand column next
# to each right-aligned "label:" (the values left-align at ~x745, measured off the
# baseline). Mask that column per visible section so the diff reflects layout +
# the Reset button, not game state — the labels + centered section titles sit well
# to the left and stay compared. Tuned to the baseline's scroll position; capture
# the Unity StatsResetBtn at a matching scroll.
STATS_VALUES = [
    (730, 340, 1160, 710),     # top partial section (values right of the colon)
    (730, 850, 1160, 1300),    # Hard section values
    (730, 1450, 1160, 1900),   # Bold section values
    (730, 2050, 1160, 2500),   # Expert section values
]

# Per-screen extra ignore regions + a max_diff (informational threshold).
SPECS = {
    "MainMenu.png":            {"ignore": [],                 "max_diff": 0.010},
    "DifficultyLevels.png":    {"ignore": [],                 "max_diff": 0.010},
    "Play.png":                {"ignore": [GAME_TABLE_CARDS], "max_diff": 0.010},
    "InGameMenu.png":          {"ignore": [INGAME_TABLE],     "max_diff": 0.010},
    "VictoryScreen1.png":      {"ignore": [VICTORY_STATS, DEV_PANEL], "max_diff": 0.010},
    "VictoryScreen2.png":      {"ignore": [VICTORY_STATS, DEV_PANEL], "max_diff": 0.010},
    "OptionsPage.png":         {"ignore": [],                 "max_diff": 0.010},
    "StatsPage.png":           {"ignore": [],                 "max_diff": 0.010},
    # Statistics has no ad banner at the bottom — the Reset button lives there — so
    # drop the shared BOTTOM_BANNER mask for this screen and keep the button compared.
    "StatsResetBtn.png":       {"ignore": STATS_VALUES,       "max_diff": 0.010,
                                "common": [STATUS_BAR]},
    "HelpPage.png":            {"ignore": [],                 "max_diff": 0.010},
    "HelpPageBottom.png":      {"ignore": [],                 "max_diff": 0.010},
    "MoreGames.png":           {"ignore": [],                 "max_diff": 0.010},
    "SpiderAboutPage.png":     {"ignore": [],                 "max_diff": 0.010},
    "SpiderFAQ.png":           {"ignore": [],                 "max_diff": 0.010},
    "choose_look_surface.png": {"ignore": [],                 "max_diff": 0.010},
    "choose_look_cards.png":   {"ignore": [],                 "max_diff": 0.010},
    "more_games_icons.png":    {"ignore": [],                 "max_diff": 0.010},
}

# Curated per-screen notes. Baseline is Obj-C 7.42.5; these describe what the
# reference shows + the known Unity deviations to check for once a Unity build is
# captured (verified per-build on the iPhone 7 / iPad — re-verify here).
META = {
    "MainMenu.png": "Settled menu WITH the left cross-promo icon strip (5 icons) — "
                    "the strip + bottom ad banner load a beat after the menu, so an "
                    "early capture misses them. Check whether Unity DROPS the strip "
                    "(it did on other devices). Logo/label sparkle-glow is volatile "
                    "(needs a volatile mask).",
    "more_games_icons.png": "Same settled menu with the promo-icon strip present.",
    "DifficultyLevels.png": "Easy/Medium/Hard/Bold/Expert picker with the smiley "
                            "cursor at 'Hard' (animated — volatile), the red 'Last "
                            "Score' ribbon, and the rotating ad banner.",
    "Play.png": "Chrome-only compare (dealt tableau + foundations/stock masked). "
                "Check the top bar (back/new/menu), hint text, and bottom ad banner.",
    "InGameMenu.png": "The replay/abandon/options/new/help/FAQ drawer on the wood "
                      "tray; dealt cards behind it are masked.",
    "VictoryScreen1.png": "First victory screen (ranking view) — no promo-icon strip "
                          "here; help/new/stats buttons are RED (were blue in an "
                          "early Unity build). Check for a stray 'Dev Panel' debug "
                          "button. Score block masked.",
    "VictoryScreen2.png": "Second victory screen — promo-icon strip present; "
                          "help/new/stats RED. Check for a 'Dev Panel' debug button. "
                          "Score block masked.",
    "OptionsPage.png": "Sounds + Cards + start of the Interface section (the taller "
                       "screen reveals Interface, which is genuine Obj-C content). "
                       "Check title case ('Options') and label typography.",
    "StatsPage.png": "NOT apples-to-apples: different play history changes the stat "
                     "VALUES. Structural check: section markers '✻' vs a plain "
                     "'*', header case.",
    "StatsResetBtn.png": "Statistics scrolled to the bottom, showing 'Reset "
                         "Statistics'. Per-run values (right of each 'label:' in the "
                         "visible sections) are masked so the diff reflects layout + "
                         "the Reset button, not game state.",
    "HelpPage.png": "Header illustration (Foundations/Source/Tableaux) + Introduction "
                    "+ Rules, single (not duplicated) Introduction, correct Spider "
                    "text. Remaining diff is typography/wrapping.",
    "HelpPageBottom.png": "Help scrolled to the bottom — Undo/Menu sections + the "
                          "'frequently asked questions' link. iPhone-14-only screen.",
    "MoreGames.png": "'Tap any game to download it!' page. The green FREE StoreKit "
                     "price pills need network (absent when captured offline); the "
                     "smiley 'tap' cursors are animated (volatile).",
    "SpiderAboutPage.png": "Title 'Spider ▷ Solitaire' with divider, version "
                           "7.42.5, '© PeopleFun', links spelled correctly "
                           "('submit feedback'). Only expected delta is the version.",
    "SpiderFAQ.png": "Spider's own FAQ (correct content, not Klondike). First entry "
                     "'How do I play the game?' appears ONCE here — check Unity for "
                     "the known DUPLICATE-first-question bug.",
    "choose_look_surface.png": "Choose-Look modal, Surface tab, 9 surface swatches + "
                               "'Simulate Depth' toggle; modal well-positioned.",
    "choose_look_cards.png": "Choose-Look modal, Cards tab, 6 card-back designs + "
                             "'Extra Large Card-Symbols' toggle ('symbols' spelled "
                             "correctly); modal well-positioned.",
}

ORDER = list(SPECS.keys())


def _load_volatile(name, shape):
    """Boolean mask of learned volatile (animated) pixels for this device's
    baseline, or all-False if none. Mirrors visual._load_volatile but reads from
    this tool's BASE_DIR so it's correct regardless of the DEVICE env var."""
    p = os.path.join(BASE_DIR, name.replace(".png", ".volatile.png"))
    if not os.path.exists(p):
        return np.zeros(shape[:2], dtype=bool)
    v = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if v is None:
        return np.zeros(shape[:2], dtype=bool)
    if v.shape != shape[:2]:
        v = cv2.resize(v, (shape[1], shape[0]))
    return v > 127


def compare_one(name, ignore, common=None):
    base = visual._gray(os.path.join(BASE_DIR, name))
    cur = visual._gray(os.path.join(UNITY_DIR, name))
    if base is None:
        return {"name": name, "status": "no-baseline", "diff_pct": None}
    if cur is None:
        return {"name": name, "status": "no-capture", "diff_pct": None}
    if base.shape != cur.shape:
        return {"name": name, "status": "size", "diff_pct": None}

    common = COMMON_IGNORE if common is None else common
    mask = visual._mask(base.shape, common + list(ignore or []))
    mask &= ~_load_volatile(name, base.shape)     # exclude learned animated pixels
    changed = visual._changed(cur, base, mask)
    compared = int(mask.sum())
    changed_px = int((changed > 0).sum())
    frac = (changed_px / compared) if compared else 0.0
    diff_path = _write_diff(name, changed, mask, frac)
    return {"name": name, "status": "ok", "diff_pct": frac * 100, "diff": diff_path}


def _write_diff(name, changed, mask, frac):
    base = cv2.imread(os.path.join(BASE_DIR, name))
    cur = cv2.imread(os.path.join(UNITY_DIR, name))
    if base is None or cur is None:
        return None
    vis = cv2.dilate(changed, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    annotated = cur.copy()
    red = annotated.copy()
    red[vis > 0] = (0, 0, 255)
    annotated = cv2.addWeighted(red, 0.55, annotated, 0.45, 0)
    for _area, (x, y, w, h) in visual._regions(changed, visual._MIN_REGION_AREA):
        cv2.rectangle(annotated, (x - 3, y - 3), (x + w + 3, y + h + 3),
                      (0, 255, 255), 3)
    annotated[~mask] = (annotated[~mask] * 0.6).astype("uint8")
    combo = np.hstack([
        visual._label(base, "iPhone 14 Pro Max  -  Obj-C 7.42.5", "baseline"),
        visual._label(annotated, "iPhone 14 Pro Max  -  Unity 8.0.0",
                      f"{frac * 100:.1f}% of compared pixels differ (red)"),
    ])
    out = os.path.join(config.LOG, "diff_ip14_" + name)
    cv2.imwrite(out, combo)
    return out


def run(report=False):
    os.makedirs(config.LOG, exist_ok=True)
    results = [compare_one(n, SPECS[n]["ignore"], SPECS[n].get("common")) for n in ORDER]

    ok = [r for r in results if r["status"] == "ok"]
    bad = [r for r in results if r["status"] != "ok"]
    print(f"\n  iPhone 14 Pro Max — Unity 8.0.0  vs  Obj-C 7.42.5   ({len(ok)}/{len(ORDER)} compared)")
    print("  " + "-" * 58)
    for r in sorted(ok, key=lambda r: r["diff_pct"], reverse=True):
        flag = "  <-- large" if r["diff_pct"] > SPECS[r["name"]]["max_diff"] * 100 else ""
        print(f"  {r['name']:<26} {r['diff_pct']:6.2f}% differ{flag}")
    for r in bad:
        print(f"  {r['name']:<26} [{r['status']}]")
    print("  " + "-" * 58)
    print(f"  diff images: {config.LOG}/diff_ip14_<name>.png")

    if report:
        import subprocess
        gen = os.path.join(config.ROOT, "scripts", "gen_versioned_report.py")
        subprocess.run([sys.executable, gen, "ip14"], check=False)
        print(f"  report:      {os.path.join(config.ROOT, 'reports', 'iPhone14_Unity_Report.html')}  (versioned, with build switcher)")
    return results


if __name__ == "__main__":
    results = run(report="--report" in sys.argv)
    # A fresh clone has no Unity captures (they live in git-ignored log/). Without
    # this the run prints a tidy summary and exits 0 having compared nothing.
    visual.exit_if_nothing_compared(
        results, UNITY_DIR, "iPhone 14 Pro Max",
        "by hand over WDA + Airtest — tidevice screenshot fails on iOS 26")
