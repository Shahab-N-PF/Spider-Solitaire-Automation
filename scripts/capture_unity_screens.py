#!/usr/bin/env python3
"""Bootstrap capture: walk the Unity build to every screen and screenshot it.

This is the chicken-and-egg step of the Unity functional suite. The suite
locates controls with templates cropped from Unity's own rendering — but to crop
those you first need captures of every screen, and to get those you must
navigate without templates. So this script navigates by COORDINATE only.

Coordinates are declared in the iPhone 14 Pro Max reference space (1290x2796,
where they were measured off log/ip14_unity_343/) and scaled to whatever the
connected device's capture size is. The iPhone 11 (828x1792) and iPhone 14 share
a 19.5:9 aspect, so a uniform scale lands within ~1% — comfortably inside a
button. It is a BOOTSTRAP, not the test suite: it is allowed to be approximate,
because everything it produces gets verified afterwards
(scripts/verify_unity_assets.py).

Output: log/unity_screens/<Name>.png, the input to scripts/crop_unity_assets.py.

Run:  ./.venv/bin/python scripts/capture_unity_screens.py
Prereqs: WDA up (scripts/wda.sh), device unlocked, Unity build installed.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import flows  # noqa: E402
import helpers  # noqa: E402
from airtest.core.api import connect_device, snapshot, swipe, touch  # noqa: E402

REF_W, REF_H = 1290, 2796          # the space the coordinates below are in
OUT = os.path.join(config.LOG, "unity_screens")

# Reference-space coordinates, measured from the iPhone 14 Unity captures.
REF = {
    "play": (1025, 1468), "stats": (959, 1666), "options": (952, 1862),
    "help": (910, 2055), "about": (980, 2245),
    "more_games": (287, 1890), "choose_look": (294, 2079),
    "logo": (644, 620),
    "back": (147, 235),            # "< back" on the red sub-screen bar
    "back_game": (144, 272),       # "< back" on the game table (sits higher)
    "easy": (1028, 1453), "medium": (1000, 1607), "hard": (913, 1778),
    "bold": (899, 1928), "expert": (956, 2096),
    "look_cards_tab": (788, 784), "look_close": (1132, 828),
    "ingame_menu": (1156, 272),
    # The first game of a session pops "Would you like to review the game rules
    # before to play?" over the table — decline it, or it covers the capture and
    # eats the next tap.
    "rules_no": (413, 1524), "rules_yes": (876, 1524),
}

_size = None


def scale(pt):
    """Reference-space (x, y) -> this device's capture space."""
    w, h = _size
    return int(pt[0] * w / REF_W), int(pt[1] * h / REF_H)


def tap(key, settle=2.0):
    touch(scale(REF[key]))
    time.sleep(settle)


def shot(name):
    path = os.path.join(OUT, name + ".png")
    snapshot(filename=path)
    print(f"  captured {name}")
    return path


def scroll_down(times=1):
    """Swipe up inside the content band to reveal what's below the fold."""
    w, h = _size
    for _ in range(times):
        swipe((w // 2, int(h * 0.75)), (w // 2, int(h * 0.30)), duration=0.4)
        time.sleep(1.0)


def to_menu(tries=4):
    """Get back to the main menu: dismiss anything up, then walk back."""
    for _ in range(tries):
        flows.dismiss_popups()
        flows.dismiss_ad(timeout=0.5)
        touch(scale(REF["back"]))
        time.sleep(1.2)
    time.sleep(1.0)


def main():
    global _size
    os.makedirs(OUT, exist_ok=True)
    helpers.launch_app()
    time.sleep(4)
    dev = connect_device(config.DEVICE_URI)
    flows.dismiss_popups()
    time.sleep(1.5)

    probe = snapshot(filename=os.path.join(OUT, "_probe.png"))
    from PIL import Image
    _size = Image.open(os.path.join(OUT, "_probe.png")).size
    print(f"device capture size: {_size[0]}x{_size[1]}  (ref {REF_W}x{REF_H})")

    # ── menu ──────────────────────────────────────────────────────
    shot("MainMenu")

    # ── simple sub-screens: open, shoot, (scroll, shoot), back ────
    for key, name, extra in [
        ("stats", "StatsPage", "StatsResetBtn"),
        ("options", "OptionsPage", None),
        ("help", "HelpPage", "HelpPageBottom"),
        ("about", "SpiderAboutPage", None),
        ("more_games", "MoreGames", None),
    ]:
        tap(key, settle=3.0)
        shot(name)
        if extra:
            scroll_down(8)
            shot(extra)
        to_menu(2)

    # ── choose look modal (closes via x, not back) ────────────────
    tap("choose_look", settle=4.0)
    shot("choose_look_surface")
    tap("look_cards_tab", settle=2.5)
    shot("choose_look_cards")
    touch(scale(REF["look_close"]))
    time.sleep(2.0)

    # ── play: difficulty picker -> table -> in-game menu bar ──────
    to_menu(1)
    tap("play", settle=2.5)
    shot("DifficultyLevels")
    tap("easy", settle=4.0)
    # Choosing a level raises "abandon the currently paused game?" (answer Yes)
    # and, on the session's first game, "review the game rules?" (answer No).
    # They look identical, so let unity_ui tell them apart by their text rather
    # than tapping a fixed button position — a no-op if those crops don't exist
    # yet, in which case the coordinate fallback below declines whatever is up.
    shot("AbandonPrompt")
    try:
        import unity_ui  # noqa: E402
        if not unity_ui.settle_prompts():
            tap("rules_no", settle=2.5)
        time.sleep(2.5)
    except Exception:  # noqa: BLE001 — bootstrap must survive a missing driver
        tap("rules_no", settle=2.5)
    shot("Play")
    touch(scale(REF["ingame_menu"]))
    time.sleep(2.0)
    shot("InGameMenu")

    print(f"\n  screens -> {OUT}")
    print("  next: ./.venv/bin/python scripts/crop_unity_assets.py --device <dev>")


if __name__ == "__main__":
    main()
