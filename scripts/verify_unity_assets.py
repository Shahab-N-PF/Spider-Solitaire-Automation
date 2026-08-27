#!/usr/bin/env python3
"""Offline quality gate for the Unity anchor templates.

A functional suite that locates controls by template is only as trustworthy as
its templates, and a bad one fails in two distinct ways:

  FRAGILE   — it doesn't match a *different* capture of the same screen. The
              menu labels sit under an animated sparkle/glow, so a crop that
              happened to include a sparkle can match its own source frame
              perfectly and nothing else. We test every template against the
              same screen captured from ANOTHER build (341 vs 343), which is an
              independent frame with the animation in a different state.
  AMBIGUOUS — it also matches a screen it has no business matching (e.g. the
              in-game "new" vs the menu-bar "new"), so an assertion built on it
              would pass on the wrong screen.

Both are checked here, with no device involved, so template breakage is caught
before it shows up as a mystery test failure.

Run:  ./.venv/bin/python scripts/verify_unity_assets.py [--thresh 0.7]
Exit status: non-zero if any template is fragile or ambiguous.
"""
import argparse
import os
import sys

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "iphone14", "assets_unity")
# Same screens, two different Unity builds -> independent frames of each screen.
BUILD_DIRS = [os.path.join(ROOT, "log", "ip14_unity_343"),
              os.path.join(ROOT, "log", "ip14_unity")]

sys.path.insert(0, ROOT)
from scripts.crop_unity_assets import CROPS  # noqa: E402  (the name -> source map)

# The "back" controls are navigation chrome: some form of them is on every
# screen but the menu, and all of them do the same thing (go up one screen), so
# a template matching another screen's back button is harmless — ui.back() tries
# each in turn. Exempt from the ambiguity check rather than listed per screen.
UNIVERSAL = {"back_bar", "back_game", "back_promo", "about_back", "stats_back"}

# Templates that legitimately appear on more than one screen — an "expected
# elsewhere" allowlist, so the ambiguity check flags only real surprises.
# Values are substrings matched against the capture's filename.
SHARED = {
    # the Help page's own footer carries the same "frequently asked questions"
    # link as the About screen (verified in the capture, not assumed)
    "about_faq": ("SpiderAboutPage", "SpiderAboutDevPanel", "HelpPageBottom"),
    "screen_stats": ("StatsPage", "StatsResetBtn"),
    "game_center": ("StatsPage", "StatsResetBtn"),
    # The menu is the same frame as the promo-strip capture, and it stays
    # VISIBLE BEHIND the Choose Look modal — which is exactly why ui.on_menu()
    # has to rule the modal out rather than trust a menu label being matchable.
    "menu_play": ("MainMenu", "more_games_icons", "choose_look"),
    "menu_stats": ("MainMenu", "more_games_icons", "choose_look"),
    "menu_options": ("MainMenu", "more_games_icons", "choose_look"),
    "menu_help": ("MainMenu", "more_games_icons", "choose_look"),
    "menu_about": ("MainMenu", "more_games_icons", "choose_look"),
    "more_games": ("MainMenu", "more_games_icons", "choose_look"),
    "choose_look": ("MainMenu", "more_games_icons", "choose_look"),
    "menu_logo": ("MainMenu", "more_games_icons", "DifficultyLevels", "choose_look", "AbandonPrompt", "Play"),
    # the Choose Look modal overlays the menu; both tabs show on both tabs
    "look_surface_tab": ("choose_look_surface", "choose_look_cards"),
    "look_cards_tab": ("choose_look_surface", "choose_look_cards"),
    "look_close": ("choose_look_surface", "choose_look_cards"),
    # the game table's top bar persists while the in-game menu bar is open
    "back_game": ("Play", "InGameMenu", "VictoryScreen"),
    "in_game_menu": ("Play", "InGameMenu", "TipDialog", "VictoryClean", "VictoryScreen"),
    "ingame_bar_new": ("Play", "InGameMenu", "TipDialog", "VictoryClean"),
    "tap_undo": ("Play", "InGameMenu", "TipDialog", "VictoryClean"),
    "tap_lower": ("Play", "InGameMenu", "TipDialog", "VictoryClean"),
    "tap_hints": ("Play", "InGameMenu", "TipDialog", "VictoryClean"),
    "tap_to_start": ("Play", "InGameMenu", "TipDialog", "VictoryClean"),
    # both victory captures are the same screen
    "screen_victory": ("VictoryScreen", "VictoryClean"),
    # Captures added later are VARIANTS of screens already listed above, so the
    # same elements legitimately appear on them: TipDialog is the game table with
    # the "Did you know?" card over it, AbandonPrompt is the difficulty picker
    # with a confirmation over it, and SpiderAboutDevPanel[Open] is the About
    # screen with the QA panel unlocked/expanded.
    "screen_about": ("SpiderAboutPage", "SpiderAboutDevPanel"),
    "about_emblem": ("SpiderAboutPage", "SpiderAboutDevPanel"),
    "about_logo": ("SpiderAboutPage", "SpiderAboutDevPanel"),
    "about_version": ("SpiderAboutPage", "SpiderAboutDevPanel"),
    "about_help": ("SpiderAboutPage", "SpiderAboutDevPanel"),
    "about_feedback": ("SpiderAboutPage", "SpiderAboutDevPanel"),
    "difficulty_easy": ("Play", "DifficultyLevels", "AbandonPrompt"),
    "difficulty_medium": ("Play", "DifficultyLevels", "AbandonPrompt"),
    "difficulty_hard": ("Play", "DifficultyLevels", "AbandonPrompt"),
    "difficulty_bold": ("Play", "DifficultyLevels", "AbandonPrompt"),
    "difficulty_expert": ("Play", "DifficultyLevels", "AbandonPrompt"),
    # The Dev Panel button follows you onto EVERY screen once the About-screen
    # gesture unlocks it, so it is expected anywhere it was captured.
    "dev_panel": ("SpiderAboutDevPanel", "TipDialog", "VictoryClean"),
    "dev_complete_game": ("SpiderAboutDevPanelOpen", "TipDialog", "VictoryClean"),
    "victory_achieve": ("VictoryScreen", "VictoryClean"),
    "victory_new": ("VictoryScreen", "VictoryClean"),
    "victory_stats": ("VictoryScreen", "VictoryClean"),
    "victory_help": ("VictoryScreen", "VictoryClean"),
    "victory_ranking": ("VictoryScreen", "VictoryClean"),
    "victory_leaderboards": ("VictoryScreen", "VictoryClean"),
    "victory_level_easy": ("VictoryScreen", "VictoryClean"),
    # Options scrolls under a FIXED top bar, so the two Options captures (the
    # top of the page and OptionsPageBottom, the same page scrolled to the end)
    # share that bar. The body rows differ, which is the point of having both.
    "screen_options": ("OptionsPage", "OptionsPageBottom"),
    "contact_us": ("OptionsPage", "OptionsPageBottom"),
}


def score(hay, needle):
    """Best normalised-correlation score of `needle` anywhere in `hay`."""
    if needle.shape[0] > hay.shape[0] or needle.shape[1] > hay.shape[1]:
        return -1.0
    return float(cv2.minMaxLoc(cv2.matchTemplate(hay, needle, cv2.TM_CCOEFF_NORMED))[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thresh", type=float, default=None,
                    help="override the threshold for every template "
                         "(default: the suite's own per-template values)")
    args = ap.parse_args()

    # Judge each template at the threshold the suite will actually use, so this
    # gate and the running suite agree. unity_ui raises the bar for templates
    # with a known near-miss elsewhere (e.g. look_cards_tab vs the Help text).
    import unity_ui  # noqa: E402

    def thresh_for(name):
        if args.thresh is not None:
            return args.thresh
        return unity_ui.THRESH.get(name, unity_ui.DEFAULT_THRESH)

    captures = {}       # (build_tag, filename) -> image
    for d in BUILD_DIRS:
        if not os.path.isdir(d):
            continue
        tag = os.path.basename(d)
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".png"):
                im = cv2.imread(os.path.join(d, fn))
                if im is not None:
                    captures[(tag, fn)] = im
    if not captures:
        sys.exit("no Unity captures found — nothing to verify against")

    fragile, ambiguous = [], []
    print(f"{'template':22} {'own':>6} {'other-build':>12}  ambiguous-on")
    print("-" * 78)

    for name in sorted(CROPS):
        path = os.path.join(ASSETS, name + ".png")
        if not os.path.exists(path):
            print(f"{name:22}   MISSING")
            fragile.append(name)
            continue
        tpl = cv2.imread(path)
        src_fn = CROPS[name][0]
        allowed = SHARED.get(name, (src_fn.replace(".png", ""),))
        thr = thresh_for(name)

        own = other = -1.0
        elsewhere = []
        for (tag, fn), im in captures.items():
            s = score(im, tpl)
            is_own_screen = any(a in fn for a in allowed)
            if is_own_screen:
                if tag == "ip14_unity_343" and fn == src_fn:
                    own = max(own, s)
                else:
                    other = max(other, s)        # same screen, different frame
            elif s >= thr and name not in UNIVERSAL:
                elsewhere.append(f"{fn[:-4]}={s:.2f}")

        flag = ""
        if other < thr:
            flag = "  <- FRAGILE"
            fragile.append(name)
        if elsewhere:
            ambiguous.append(name)
        print(f"{name:22} {own:6.3f} {other:12.3f}  "
              f"{','.join(elsewhere[:3]) if elsewhere else '-'}{flag}")

    print("-" * 78)
    print(f"  {len(CROPS)} templates (per-template thresholds from unity_ui)")
    if fragile:
        print(f"  FRAGILE ({len(fragile)}): {', '.join(fragile)}")
        print("    -> matches its own frame but not another capture of the same "
              "screen; re-crop away from animated glow/sparkle.")
    if ambiguous:
        print(f"  AMBIGUOUS ({len(ambiguous)}): {', '.join(ambiguous)}")
        print("    -> also matches an unrelated screen; tighten the crop or add "
              "it to SHARED if that's expected.")
    if not fragile and not ambiguous:
        print("  all templates match across builds and are screen-unique")
    return 1 if (fragile or ambiguous) else 0


if __name__ == "__main__":
    sys.exit(main())
