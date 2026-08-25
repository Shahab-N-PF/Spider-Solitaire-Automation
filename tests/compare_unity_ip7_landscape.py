#!/usr/bin/env python3
"""Compare the iPhone 7 **LANDSCAPE** Unity build's screens against the iPhone 7
**landscape Obj-C** baselines (the landscape analog of tests/compare_unity_ip7.py).

Spider's landscape UI is a genuine reflow, NOT a rotation of portrait — the menu
arc moves to the right, the logo sits left-of-center, and the tableau spreads
across ten columns — so it has its own 1334x750 baselines and its own mask
regions (measured off real landscape captures, never scaled from portrait).

The iPhone 7 (iOS 15.7.5) can't run WDA under Xcode 26.5 (see iphone7/README.md),
so both sets are captured MANUALLY via tidevice `screenshot` with the phone
rotated to landscape. tidevice returns the framebuffer in the device's native
PORTRAIT orientation (750x1334) even while the game renders landscape, so each
capture is rotated 90° counter-clockwise to a true upright 1334x750 before use:
  - Obj-C 7.42.5  -> iphone7/landscape/baselines/<name>.png   (the reference)
  - Unity 8.0.0   -> log/ip7_landscape_unity/<name>.png        (this run's captures)

This script exact-pixel diffs each Unity capture against its Obj-C baseline with
iPhone-7 landscape (1334x750) mask regions, subtracts any learned volatile-pixel
mask (iphone7/landscape/baselines/<name>.volatile.png), writes
log/diff_ip7ls_<name>.png (baseline | Unity with differing pixels in red + boxed),
and prints a per-screen diff% summary (ranked, worst first). `--report`
regenerates the versioned report via scripts/gen_versioned_report.py.

Run:
  ./.venv/bin/python tests/compare_unity_ip7_landscape.py            # diff + summary
  ./.venv/bin/python tests/compare_unity_ip7_landscape.py --report   # + HTML report
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import config  # noqa: E402
import visual  # noqa: E402

UNITY_DIR = os.path.join(config.LOG, "ip7_landscape_unity")   # Unity 8.0.0 captures
BASE_DIR = os.path.join(config.ROOT, "iphone7", "landscape", "baselines")  # Obj-C 7.42.5

# iPhone 7 landscape = 1334x750 (portrait 750x1334 with dimensions swapped). The
# game runs FULLSCREEN in landscape — there is NO iOS status bar to mask (unlike
# the portrait / iPhone-14 tools). The only universal volatile chrome is the
# bottom cross-promo ad banner, which only appears on the game/menu surfaces, so
# it is added per-screen (below) rather than to COMMON_IGNORE.
W, H = 1334, 750
BOTTOM_BANNER = (0, 610, W, H)      # rotating house ad banner in its wood frame
                                    # (game content ends ~575; banner solid ~616-714)
COMMON_IGNORE = []                  # nothing is masked on every screen in landscape

# Play: the dealt tableau + foundation + source deck fill the top ~57% and are
# random per game; the waste pile + score/time/multiplier + hint pile sit in a
# band along the bottom-center. Mask both so the diff reflects fixed chrome
# (back / menu / undo & hint labels) not game state.
PLAY_CARDS = (0, 0, W, 425)             # tableau row + foundation + source + centre text
PLAY_WIDGETS = (255, 498, 1060, 592)    # waste pile + score/time/X-mult + hint pile
INGAME_TABLE = PLAY_CARDS               # same dealt cards behind the in-game menu tray

# Victory screens show a run-dependent "won N" line plus the current/rank/best
# numeric table; mask both so the diff reflects layout (promo strip, red buttons,
# right-hand labels) not game state. The "current/rank/best" column headers sit
# above the table and stay compared.
VICTORY_STATS = [
    (355, 175, 965, 465),   # current / rank / best numeric table
    (525, 60, 835, 100),    # "won N ✧ M abandoned" line
]
# Build 345 still ships a development-only "Dev Panel" button at the bottom-right of
# both victory screens (present since 343). Masked by request so it does not drive the
# diff — mirrors the iPhone 14 DEV_PANEL region. Sits right of the stats button, below
# "menu", so neither is clipped.
DEV_PANEL_LS = (1160, 525, W, 610)

# Last Won Game Score: reached from the menu, it's the victory ranking view stamped
# with the current DATE ("Week of <date>" + a "<date>" on the right). The date moves
# with the calendar, so mask it along with the "won N" line and the current/rank/best
# table — otherwise every future run false-diffs on the date and play history. There
# is no ad banner on this screen; header, headers, "easy level", and the
# scores/time/moves/run labels stay compared.
LASTSCORE = [
    (490, 178, 850, 222),    # "Week of <date>" line (between the ‹ › arrows)
    (525, 226, 815, 258),    # "won N ✧ M abandoned" line
    (355, 340, 950, 615),    # current / rank / best numeric table
    (1095, 345, 1255, 385),  # "<date>" stamp on the right
]

# Statistics is a two-column layout: left-column values sit right of each
# left-label's colon (~x460+), right-column values right of each right-label's
# colon (~x930+). Mask those value cells per visible section so the diff reflects
# layout/typography + (on StatsResetBtn) the Reset button — NOT play history. The
# centred "✻ Section ✻" markers stay compared (a key ✻-vs-'*' check), as do all
# labels and the Reset Statistics button.
STATS_VALUES_PAGE = [                    # StatsPage (top: summary + Easy + Medium)
    (460, 105, 610, 200), (930, 105, 1090, 200),    # overall summary
    (460, 295, 610, 430), (930, 295, 1090, 430),    # Easy
    (460, 518, 610, 655), (930, 518, 1090, 655),    # Medium
]
STATS_VALUES_RESET = [                   # StatsResetBtn (bottom: Hard tail + Bold + Expert)
    (460, 68, 610, 108),  (930, 68, 1090, 108),     # tail of Hard section
    (460, 208, 610, 342), (930, 208, 1090, 342),    # Bold
    (460, 440, 610, 568), (930, 440, 1090, 568),    # Expert
]

# Per-screen extra ignore regions + a max_diff (informational threshold). Screens
# that carry the rotating ad banner get BOTTOM_BANNER; the settings/menu screens
# (Options/Help/FAQ/About/Stats) have no banner and content that reaches the
# bottom, so they are compared in full.
SPECS = {
    "MainMenu.png":            {"ignore": [BOTTOM_BANNER],              "max_diff": 0.010},
    "DifficultyLevels.png":    {"ignore": [BOTTOM_BANNER],              "max_diff": 0.010},
    "Play.png":                {"ignore": [PLAY_CARDS, PLAY_WIDGETS, BOTTOM_BANNER], "max_diff": 0.010},
    "InGameMenu.png":          {"ignore": [INGAME_TABLE, BOTTOM_BANNER], "max_diff": 0.010},
    "VictoryScreen1.png":      {"ignore": VICTORY_STATS + [BOTTOM_BANNER, DEV_PANEL_LS], "max_diff": 0.010},
    "VictoryScreen2.png":      {"ignore": VICTORY_STATS + [BOTTOM_BANNER, DEV_PANEL_LS], "max_diff": 0.010},
    "LastScore.png":           {"ignore": LASTSCORE,                   "max_diff": 0.010},
    "OptionsPage.png":         {"ignore": [],                          "max_diff": 0.010},
    "StatsPage.png":           {"ignore": STATS_VALUES_PAGE,           "max_diff": 0.010},
    "StatsResetBtn.png":       {"ignore": STATS_VALUES_RESET,          "max_diff": 0.010},
    "HelpPage.png":            {"ignore": [],                          "max_diff": 0.010},
    "MoreGames.png":           {"ignore": [],                          "max_diff": 0.010},
    "SpiderAboutPage.png":     {"ignore": [],                          "max_diff": 0.010},
    "SpiderFAQ.png":           {"ignore": [],                          "max_diff": 0.010},
    "choose_look_surface.png": {"ignore": [BOTTOM_BANNER],             "max_diff": 0.010},
    "choose_look_cards.png":   {"ignore": [BOTTOM_BANNER],             "max_diff": 0.010},
    "more_games_icons.png":    {"ignore": [BOTTOM_BANNER],             "max_diff": 0.010},
}

# Curated notes shown in the report. Landscape Unity has not been captured yet, so
# these describe the Obj-C reference + what to check on the Unity landscape build
# (carrying over the known cross-device findings: lowercase "options", '✻' vs '*'
# markers, dropped ad banner, typography/wrap drift, and — now fixed on build 341 —
# the FAQ duplicate-first-question and the victory "Dev Panel" debug button).
META = {
    "MainMenu.png": "Landscape reflow: menu arc (Play/Stats/Options/Help/About) on "
                    "the RIGHT, Spider logo left-of-centre, More Games/Choose Look "
                    "bottom-left, wood frame along the bottom. Logo/label glow is "
                    "animated (may need a volatile mask); ad banner masked.",
    "more_games_icons.png": "Same settled menu with the left cross-promo icon strip "
                            "loaded (Solitaire / Sudoku² / Card Games / FreeCell / "
                            "Spiderette). Ad banner masked.",
    "DifficultyLevels.png": "Easy/Medium/Hard/Bold/Expert arc on the right with the "
                            "smiley cursor at 'Hard' (animated — may need a volatile "
                            "mask), 'Last Score' label + red ribbon bottom-right. "
                            "A per-run Last-Score value may differ vs the baseline.",
    "Play.png": "Chrome-only compare (dealt tableau + foundation + source + the "
                "waste/score/hint widgets are masked). Check back/menu, the undo & "
                "hint labels, and whether Unity drops the bottom ad banner (Obj-C "
                "shows one).",
    "InGameMenu.png": "The replay/abandon/help/options/new/FAQ tray on the wood "
                      "strip with the restart button at the left; dealt cards behind "
                      "it and the ad banner are masked.",
    "VictoryScreen1.png": "First victory (ranking) view — left promo-icon strip, "
                          "help/new/stats buttons should be RED. Check for a stray "
                          "'Dev Panel' debug button (bottom-right). won-count + "
                          "score/rank/best table masked.",
    "VictoryScreen2.png": "Second victory view — 'best' column populated, promo strip "
                          "present, help/new/stats RED. Check for a 'Dev Panel' debug "
                          "button. won-count + score/rank/best table masked.",
    "LastScore.png": "'Last Won Game Score' — the ranking view reached from the menu, "
                     "stamped with the current DATE ('Week of <date>' + '<date>'). The "
                     "date, the won-count, and the current/rank/best table are masked "
                     "(they track the calendar + play history), so the diff reflects "
                     "the header, the current/rank/best labels, and the "
                     "scores/time/moves/run labels.",
    "OptionsPage.png": "Sounds section (Applause/Effects sliders + Auto-Mute toggle). "
                       "Check the title case — Obj-C is capitalised 'Options'; Unity "
                       "has shipped a lowercase 'options' on other devices.",
    "StatsPage.png": "NOT apples-to-apples: play history changes the stat VALUES "
                     "(masked). Structural check: section markers decorative '✻' vs "
                     "a plain '*', and header case.",
    "StatsResetBtn.png": "Statistics scrolled to the bottom (Hard tail / Bold / "
                         "Expert + the gold 'Reset Statistics' button). Per-run values "
                         "are masked so the diff reflects layout + the Reset button.",
    "HelpPage.png": "Header illustration (Foundations / Tableaux / Source) + "
                    "Introduction + Rules. Check for a single (not duplicated) "
                    "Introduction and correct Spider text; remaining diff is "
                    "typography / line-wrap.",
    "MoreGames.png": "Red-curtain 'stage' promo (Solitaire + FREE, Sudoku² + smiley, "
                     "'Tap any game to download it!'). Animated + StoreKit-driven, so "
                     "expect volatile content; may list different titles vs Obj-C.",
    "SpiderAboutPage.png": "Title 'Spider ▷ Solitaire' with the ▷ divider, version "
                           "7.42.5, '© PeopleFun', links spelled correctly ('submit "
                           "feedback'). Only expected delta is the version string.",
    "SpiderFAQ.png": "Spider's own FAQ content (correct, not Klondike). The first "
                     "entry 'How do I play the game?' appears ONCE here — check the "
                     "Unity build for the (now-fixed on 341) duplicate-first-question.",
    "choose_look_surface.png": "Choose-Look modal, Surface tab — 9 surface swatches + "
                               "'Simulate Depth' toggle; dimmed menu behind. Ad banner "
                               "masked; check modal position/scale.",
    "choose_look_cards.png": "Choose-Look modal, Cards tab — 6 card-back designs + "
                             "'Extra Large Card-Symbols' toggle ('symbols' spelled "
                             "correctly). Ad banner masked; check modal position/scale.",
}

ORDER = list(SPECS.keys())


def _load_volatile(name, shape):
    """Boolean mask of learned volatile (animated) pixels for this device/
    orientation's baseline, or all-False if none. Mirrors visual._load_volatile
    but reads from this tool's BASE_DIR so it's correct regardless of DEVICE."""
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
        visual._label(base, "iPhone 7 (landscape)  -  Obj-C 7.42.5", "baseline"),
        visual._label(annotated, "iPhone 7 (landscape)  -  Unity 8.0.0",
                      f"{frac * 100:.1f}% of compared pixels differ (red)"),
    ])
    out = os.path.join(config.LOG, "diff_ip7ls_" + name)
    cv2.imwrite(out, combo)
    return out


def run(report=False):
    os.makedirs(config.LOG, exist_ok=True)
    results = [compare_one(n, SPECS[n]["ignore"], SPECS[n].get("common")) for n in ORDER]

    ok = [r for r in results if r["status"] == "ok"]
    bad = [r for r in results if r["status"] != "ok"]
    print(f"\n  iPhone 7 landscape — Unity 8.0.0  vs  Obj-C 7.42.5   ({len(ok)}/{len(ORDER)} compared)")
    print("  " + "-" * 58)
    for r in sorted(ok, key=lambda r: r["diff_pct"], reverse=True):
        flag = "  <-- large" if r["diff_pct"] > SPECS[r["name"]]["max_diff"] * 100 else ""
        print(f"  {r['name']:<26} {r['diff_pct']:6.2f}% differ{flag}")
    for r in bad:
        print(f"  {r['name']:<26} [{r['status']}]")
    print("  " + "-" * 58)
    print(f"  diff images: {config.LOG}/diff_ip7ls_<name>.png")

    if report:
        import subprocess
        gen = os.path.join(config.ROOT, "scripts", "gen_versioned_report.py")
        subprocess.run([sys.executable, gen, "ip7-landscape"], check=False)
        print(f"  report:      {os.path.join(config.ROOT, 'reports', 'iPhone7_Landscape_Unity_Report.html')}  (versioned, with build switcher)")
    return results


if __name__ == "__main__":
    results = run(report="--report" in sys.argv)
    # A fresh clone has no Unity captures (they live in git-ignored log/). Without
    # this the run prints a tidy summary and exits 0 having compared nothing.
    visual.exit_if_nothing_compared(
        results, UNITY_DIR, "iPhone 7 (landscape)",
        "tidevice launch + screenshot, by hand, phone held landscape")
