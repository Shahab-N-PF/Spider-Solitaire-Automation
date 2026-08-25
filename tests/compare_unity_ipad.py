#!/usr/bin/env python3
"""Compare the iPad **Unity** build's screens against the iPad **Obj-C** baselines
(the iPad analog of tests/compare_unity_ip7.py).

The iPad (iOS 26.3.1) can't be screenshotted by tidevice (DeveloperImage won't
mount), so both sets are captured over **WDA + Airtest** (see ipad/README.md):
  - Obj-C 7.42.5  -> ipad/baselines/<name>.png   (the reference)
  - Unity 8.0.0   -> ipad/unity/<name>.png        (this run's captures)

Exact-pixel diffs each Unity capture against its Obj-C baseline with iPad
(1620x2160) mask regions, writes log/diff_ipad_<name>.png (baseline | Unity with
differing pixels in red + boxed), prints a per-screen diff% summary (worst first).
`--report` also writes log/ipad_unity_compare.html.

Run:
  ./.venv/bin/python tests/compare_unity_ipad.py            # diff + summary
  ./.venv/bin/python tests/compare_unity_ipad.py --report   # + HTML report
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import config  # noqa: E402
import visual  # noqa: E402

UNITY_DIR = os.path.join(config.ROOT, "ipad", "unity")         # Unity 8.0.0 captures
BASE_DIR = os.path.join(config.ROOT, "ipad", "baselines")      # Obj-C 7.42.5

# iPad (9th gen) = 1620x2160 portrait. Volatile chrome to ignore everywhere:
W, H = 1620, 2160
STATUS_BAR = (0, 0, W, 70)          # iOS status bar (time / battery), when shown
BOTTOM_BANNER = (0, 1940, W, H)     # rotating cross-promo / house ad banner
COMMON_IGNORE = [STATUS_BAR, BOTTOM_BANNER]

GAME_TABLE_CARDS = (0, 150, W, 1060)  # the randomly-dealt tableau + stock on Play
INGAME_TABLE = (0, 150, W, 1060)      # dealt cards behind the in-game menu panel
# Victory screens show run-dependent score/time/moves numbers; mask the stat block.
VICTORY_STATS = (300, 820, W - 300, 1320)

# Per-screen extra ignore regions + a max_diff (informational threshold).
SPECS = {
    "MainMenu.png":            {"ignore": [],                 "max_diff": 0.010},
    "DifficultyLevels.png":    {"ignore": [],                 "max_diff": 0.010},
    "Play.png":                {"ignore": [GAME_TABLE_CARDS], "max_diff": 0.010},
    "InGameMenu.png":          {"ignore": [INGAME_TABLE],     "max_diff": 0.010},
    "VictoryScreen1.png":      {"ignore": [VICTORY_STATS],    "max_diff": 0.010},
    "VictoryScreen2.png":      {"ignore": [VICTORY_STATS],    "max_diff": 0.010},
    "OptionsPage.png":         {"ignore": [],                 "max_diff": 0.010},
    "StatsPage.png":           {"ignore": [],                 "max_diff": 0.010},
    "HelpPage.png":            {"ignore": [],                 "max_diff": 0.010},
    "MoreGames.png":           {"ignore": [],                 "max_diff": 0.010},
    "SpiderAboutPage.png":     {"ignore": [],                 "max_diff": 0.010},
    "SpiderFAQ.png":           {"ignore": [],                 "max_diff": 0.010},
    "choose_look_surface.png": {"ignore": [],                 "max_diff": 0.010},
    "choose_look_cards.png":   {"ignore": [],                 "max_diff": 0.010},
    "more_games_icons.png":    {"ignore": [],                 "max_diff": 0.010},
}

# Curated findings observed during capture (shown in the report).
# Build under test: iPad Unity 8.0.0 (second Unity build; many prior findings fixed).
META = {
    "SpiderFAQ.png": "FAQ content is now CORRECT (Spider's own questions — the "
                     "prior 'wrong game' Klondike content is fixed), BUT the first "
                     "entry 'How do I play the game?' is DUPLICATED (appears twice, "
                     "back-to-back).",
    "HelpPage.png": "Content correct and not duplicated. Remaining diff is "
                    "typography: Unity wraps text heavier/larger so every line "
                    "shifts, plus the header illustration differs.",
    "SpiderAboutPage.png": "Clean match: title 'Spider > Solitaire' with divider, "
                           "'submit feedback' spelled correctly. Only real delta is "
                           "version 8.0.0 vs baseline 7.42.5 (expected).",
    "choose_look_cards.png": "Description reads 'symbols' (correct); modal now "
                             "well-positioned. Card-back grid order may still differ "
                             "slightly vs Obj-C.",
    "MainMenu.png": "FIXED: the left cross-promo icon strip is back (was dropped in "
                    "the prior build). The promo icons + ad banner load a beat after "
                    "the menu. Logo/label sparkle-glow animation differs (volatile — "
                    "needs a volatile mask).",
    "more_games_icons.png": "Main-menu view; the left promo-icon strip is present "
                            "now (fixed).",
    "StatsPage.png": "NOT apples-to-apples: different play history than the baseline, "
                     "so the stat VALUES differ. Structural note: section markers are "
                     "plain '*' vs Obj-C's decorative '*', and headers are lowercase.",
    "OptionsPage.png": "Content matches (Sounds + Cards). Diffs: lowercase 'options' "
                       "title and heavier label typography.",
    "DifficultyLevels.png": "FIXED: the smiley cursor at 'Hard' is back and the extra "
                            "'More Games'/'Choose Look' entries are gone (both were "
                            "prior-build issues). Ad banner differs (rotating).",
    "Play.png": "Chrome-only compare (dealt cards masked). Unity has no bottom ad "
                "banner (Obj-C shows one); top bar + hint text differ.",
    "MoreGames.png": "Unity lists more titles (Solitaire / Sudoku 2 / Card Games) "
                     "and shifts the layout vs Obj-C's two games.",
    "choose_look_surface.png": "FIXED: the Choose-Look modal is now well-positioned "
                               "(prior build rendered it shifted down and enlarged). "
                               "Close match apart from the rotating ad banner.",
    "InGameMenu.png": "The replay/abandon/options/new/help/FAQ panel differs in the "
                      "bottom tray — different wood/button rendering and Unity drops "
                      "the ad banner. Dealt cards masked.",
    "VictoryScreen1.png": "FIXED: no promo-icon strip on the first victory screen "
                          "(prior build wrongly added one) and help/new/stats buttons "
                          "are RED again (were blue). Score block masked.",
    "VictoryScreen2.png": "help/new/stats buttons are RED now (fixed). NEW ISSUE: a "
                          "'Dev Panel' debug button is visible bottom-right — a "
                          "development control that should not ship. Score masked.",
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
        visual._label(base, "iPad  -  Obj-C 7.42.5", "baseline"),
        visual._label(annotated, "iPad  -  Unity 8.0.0",
                      f"{frac * 100:.1f}% of compared pixels differ (red)"),
    ])
    out = os.path.join(config.LOG, "diff_ipad_" + name)
    cv2.imwrite(out, combo)
    return out


def run(report=False):
    os.makedirs(config.LOG, exist_ok=True)
    results = [compare_one(n, SPECS[n]["ignore"]) for n in ORDER]

    ok = [r for r in results if r["status"] == "ok"]
    bad = [r for r in results if r["status"] != "ok"]
    print(f"\n  iPad — Unity 8.0.0  vs  Obj-C 7.42.5   ({len(ok)}/{len(ORDER)} compared)")
    print("  " + "-" * 58)
    for r in sorted(ok, key=lambda r: r["diff_pct"], reverse=True):
        flag = "  <-- large" if r["diff_pct"] > SPECS[r["name"]]["max_diff"] * 100 else ""
        print(f"  {r['name']:<26} {r['diff_pct']:6.2f}% differ{flag}")
    for r in bad:
        print(f"  {r['name']:<26} [{r['status']}]")
    print("  " + "-" * 58)
    print(f"  diff images: {config.LOG}/diff_ipad_<name>.png")

    if report:
        import subprocess
        gen = os.path.join(config.ROOT, "scripts", "gen_versioned_report.py")
        subprocess.run([sys.executable, gen, "ipad"], check=False)
        print(f"  report:      {os.path.join(config.ROOT, 'reports', 'ipad_unity_report.html')}  (versioned, with build switcher)")
    return results


if __name__ == "__main__":
    results = run(report="--report" in sys.argv)
    # A fresh clone has no Unity captures (they live in git-ignored log/). Without
    # this the run prints a tidy summary and exits 0 having compared nothing.
    visual.exit_if_nothing_compared(
        results, UNITY_DIR, "iPad",
        "already committed to ipad/unity/ — if it is empty your checkout is incomplete")
