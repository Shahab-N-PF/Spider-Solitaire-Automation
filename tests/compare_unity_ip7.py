#!/usr/bin/env python3
"""Compare the iPhone 7 **Unity** build's screens against the iPhone 7 **Obj-C**
baselines (the iPhone-7 analog of tests/compare_unity.py).

The iPhone 7 (iOS 15.7.5) can't run WDA under Xcode 26.5 (see iphone7/README.md),
so both sets are captured MANUALLY via tidevice `screenshot`:
  - Obj-C 7.42.5  -> iphone7/portrait/baselines/<name>.png   (the reference)
  - Unity 8.0.0   -> log/ip7_unity/<name>.png        (this run's captures)

This script exact-pixel diffs each Unity capture against its Obj-C baseline with
iPhone-7 (750x1334) mask regions, writes log/diff_ip7_<name>.png (baseline | Unity
with differing pixels in red + boxed), and prints a per-screen diff% summary
(ranked, worst first). `--report` also writes log/ip7_unity_compare.html — a
drag-to-wipe viewer with the curated per-screen findings.

Run:
  ./.venv/bin/python tests/compare_unity_ip7.py            # diff + summary
  ./.venv/bin/python tests/compare_unity_ip7.py --report   # + HTML report
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import config  # noqa: E402
import visual  # noqa: E402

UNITY_DIR = os.path.join(config.LOG, os.environ.get("IP7_UNITY_DIR", "ip7_unity"))
# ^ Unity captures. Override with IP7_UNITY_DIR to diff a different build,
#   e.g. IP7_UNITY_DIR=ip7_unity_343. Per-build dirs: ip7_unity_343 (343),
#   ip7_unity_341 (341), ip7_unity_prevbuild (335).
BASE_DIR = os.path.join(config.ROOT, "iphone7", "portrait", "baselines")  # Obj-C 7.42.5

# iPhone 7 = 750x1334. Volatile chrome to ignore everywhere:
W, H = 750, 1334
STATUS_BAR = (0, 0, W, 44)          # iOS status bar (time / battery), when shown
BOTTOM_BANNER = (0, 1160, W, H)     # rotating cross-promo house banner (top edge ~1160;
                                    # above the victory buttons, which end ~1120)
COMMON_IGNORE = [STATUS_BAR, BOTTOM_BANNER]

GAME_TABLE_CARDS = (0, 88, W, 512)  # the randomly-dealt tableau on Play
INGAME_TABLE = (0, 88, W, 512)      # dealt cards behind the in-game menu panel
# Victory screens show run-dependent score/time/moves numbers (see META); mask the
# stat block + the top ace/stock cards so the diff reflects layout, not game state.
VICTORY_STATS = (60, 480, W - 60, 900)
# Last Won Game Score (reached from the menu): the victory ranking view stamped with
# the current DATE ("Week of <date>" + a "<date>" near the bottom), plus the "won N"
# line and the current/rank/best table — all track the calendar / play history, so
# mask them. There is NO ad banner here and the scores/time/moves/run labels sit below
# the banner's top edge, so this screen drops the shared BOTTOM_BANNER (see `common`).
LASTSCORE = [
    (180, 448, 570, 492),    # "Week of <date>" line (between the ‹ › arrows)
    (225, 494, 525, 528),    # "won N ✧ M abandoned" line
    (80, 625, 645, 900),     # current / rank / best numeric table
    (280, 1108, 470, 1145),  # "<date>" stamp near the bottom
]
# Statistics screen: the value column (right of each "label:" colon) holds per-run
# numbers that vary by play history. Mask the three sections' value columns so the
# diff reflects layout/typography + the Reset Statistics button, not game state.
# Labels, section headers, and the Reset button stay compared.
STATS_VALUES = [
    (425, 180, 660, 445),    # Hard section values
    (425, 535, 660, 800),    # Bold section values
    (425, 890, 660, 1160),   # Expert section values
]

# Per-screen extra ignore regions + a max_diff (informational threshold).
SPECS = {
    "MainMenu.png":            {"ignore": [],                 "max_diff": 0.010},
    "DifficultyLevels.png":    {"ignore": [],                 "max_diff": 0.010},
    "Play.png":                {"ignore": [GAME_TABLE_CARDS], "max_diff": 0.010},
    "InGameMenu.png":          {"ignore": [INGAME_TABLE],     "max_diff": 0.010},
    "VictoryScreen1.png":      {"ignore": [VICTORY_STATS],    "max_diff": 0.010},
    "VictoryScreen2.png":      {"ignore": [VICTORY_STATS],    "max_diff": 0.010},
    # Last Won Game Score has no ad banner and its scores/time/moves/run labels sit
    # below the banner's top edge, so drop the shared BOTTOM_BANNER for this screen.
    "LastScore.png":           {"ignore": LASTSCORE,          "max_diff": 0.010,
                                "common": [STATUS_BAR]},
    "OptionsPage.png":         {"ignore": [],                 "max_diff": 0.010},
    "StatsPage.png":           {"ignore": [],                 "max_diff": 0.010},
    # Statistics has no ad banner at the bottom — the Reset button lives there — so
    # drop the shared BOTTOM_BANNER mask for this screen and keep the button compared.
    "StatsResetBtn.png":       {"ignore": STATS_VALUES,       "max_diff": 0.010,
                                "common": [STATUS_BAR]},
    "HelpPage.png":            {"ignore": [],                 "max_diff": 0.010},
    "MoreGames.png":           {"ignore": [],                 "max_diff": 0.010},
    "SpiderAboutPage.png":     {"ignore": [],                 "max_diff": 0.010},
    "SpiderFAQ.png":           {"ignore": [],                 "max_diff": 0.010},
    "choose_look_surface.png": {"ignore": [],                 "max_diff": 0.010},
    "choose_look_cards.png":   {"ignore": [],                 "max_diff": 0.010},
    "more_games_icons.png":    {"ignore": [],                 "max_diff": 0.010},
}

# Curated findings observed during capture (shown in the report).
# Build under test: Unity 8.0.0 (third Unity build; most prior-build bugs fixed).
META = {
    "SpiderFAQ.png": "FAQ content is now CORRECT (Spider's own questions — the "
                     "prior build's 'wrong game' Klondike content is fixed), BUT the "
                     "first entry 'How do I play the game?' is DUPLICATED (appears "
                     "twice, back-to-back).",
    "HelpPage.png": "Single (not duplicated) 'Introduction' and correct text. "
                    "Remaining diff is typography: Unity wraps lines heavier/larger "
                    "so every line shifts, plus the header illustration differs.",
    "SpiderAboutPage.png": "Clean match: title 'Spider ▷ Solitaire' with divider, "
                           "'submit feedback' spelled correctly. Only real delta is "
                           "version 8.0.0 vs baseline 7.42.5 (expected).",
    "choose_look_cards.png": "Description reads 'symbols' (correct); modal "
                             "well-positioned. Card-back grid order may still differ "
                             "slightly vs Obj-C.",
    "MainMenu.png": "FIXED: the left cross-promo icon strip is back (was dropped in "
                    "the prior build). The promo icons + ad banner load a beat after "
                    "the menu. Logo/label sparkle-glow animation differs (volatile — "
                    "needs a volatile mask).",
    "more_games_icons.png": "Main-menu view; the left promo-icon strip is present "
                            "now (fixed).",
    "StatsPage.png": "NOT apples-to-apples: games were played on the Unity device, "
                     "so the stat VALUES differ from the fresh-install baseline. "
                     "Structural note: section markers are plain '*' vs Obj-C's "
                     "decorative '✻', and headers are lowercase.",
    "StatsResetBtn.png": "Statistics scrolled to the bottom, showing the 'Reset "
                         "Statistics' button. Per-run stat values (right of each "
                         "'label:' colon in the Hard/Bold/Expert sections) are masked "
                         "so the diff reflects layout/typography + the Reset button, "
                         "not game state. Section markers are plain '*' vs Obj-C's "
                         "decorative '✻', and headers are lowercase (as on StatsPage).",
    "OptionsPage.png": "Content matches (Sounds + Cards). Diff is typography — "
                       "lowercase 'options' title and heavier label rendering.",
    "DifficultyLevels.png": "FIXED: the smiley cursor at 'Hard' is back and the "
                            "stray 'More Games'/'Choose Look' entries are gone (both "
                            "prior-build issues). Ad banner differs (rotating).",
    "Play.png": "Chrome-only compare (dealt cards masked). Unity has no bottom ad "
                "banner (Obj-C shows one); top bar + hint text differ.",
    "MoreGames.png": "Same promo page but Unity lists more titles (Solitaire / "
                     "Sudoku² / Card Games Platinum) and shifts the layout vs Obj-C.",
    "choose_look_surface.png": "Close match to Obj-C (Surface tab, 9 swatches, "
                               "Simulate Depth toggle); modal well-positioned.",
    "InGameMenu.png": "Close match — replay/abandon/options/new/help/FAQ panel on "
                      "the wood tray. Unity drops the bottom ad banner; dealt cards "
                      "behind the panel are masked.",
    "VictoryScreen1.png": "FIXED: no promo-icon strip on the first victory screen "
                          "(prior build wrongly added one) and help/new/stats buttons "
                          "are RED again (were blue). NEW ISSUE: a 'Dev Panel' debug "
                          "button is visible bottom-right. Score block masked.",
    "VictoryScreen2.png": "help/new/stats buttons are RED now (fixed); promo strip "
                          "present (correct). NEW ISSUE: a 'Dev Panel' debug button "
                          "is visible bottom-right — should not ship. Score masked.",
    "LastScore.png": "'Last Won Game Score' — the ranking view reached from the menu, "
                     "stamped with the current DATE ('Week of <date>' + '<date>'). The "
                     "date, won-count, and current/rank/best table are masked (they "
                     "track the calendar + play history), so the diff reflects the "
                     "header, the current/rank/best labels, and the "
                     "scores/time/moves/run labels.",
}

ORDER = list(SPECS.keys())


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
        visual._label(base, "iPhone 7  -  Obj-C 7.42.5", "baseline"),
        visual._label(annotated, "iPhone 7  -  Unity 8.0.0",
                      f"{frac * 100:.1f}% of compared pixels differ (red)"),
    ])
    out = os.path.join(config.LOG, "diff_ip7_" + name)
    cv2.imwrite(out, combo)
    return out


def run(report=False):
    os.makedirs(config.LOG, exist_ok=True)
    results = [compare_one(n, SPECS[n]["ignore"], SPECS[n].get("common")) for n in ORDER]

    ok = [r for r in results if r["status"] == "ok"]
    bad = [r for r in results if r["status"] != "ok"]
    print(f"\n  iPhone 7 — Unity 8.0.0  vs  Obj-C 7.42.5   ({len(ok)}/{len(ORDER)} compared)")
    print("  " + "-" * 58)
    for r in sorted(ok, key=lambda r: r["diff_pct"], reverse=True):
        flag = "  <-- large" if r["diff_pct"] > SPECS[r["name"]]["max_diff"] * 100 else ""
        print(f"  {r['name']:<26} {r['diff_pct']:6.2f}% differ{flag}")
    for r in bad:
        print(f"  {r['name']:<26} [{r['status']}]")
    print("  " + "-" * 58)
    print(f"  diff images: {config.LOG}/diff_ip7_<name>.png")

    if report:
        import subprocess
        gen = os.path.join(config.ROOT, "scripts", "gen_versioned_report.py")
        subprocess.run([sys.executable, gen, "ip7"], check=False)
        print(f"  report:      {os.path.join(config.ROOT, 'reports', 'iPhone7_Unity_Report.html')}  (versioned, with build switcher)")
    return results


if __name__ == "__main__":
    results = run(report="--report" in sys.argv)
    # A fresh clone has no Unity captures (they live in git-ignored log/). Without
    # this the run prints a tidy summary and exits 0 having compared nothing.
    visual.exit_if_nothing_compared(
        results, UNITY_DIR, "iPhone 7 (portrait)",
        "tidevice launch + screenshot, by hand — no WDA on iOS 15")
