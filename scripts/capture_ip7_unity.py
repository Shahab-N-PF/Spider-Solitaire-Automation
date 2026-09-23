#!/usr/bin/env python3
"""Guided iPhone 7 Unity capture via tidevice (no WDA).

Launches Spider, then waits for the on-device UI to change and settle
before writing each expected comparison screenshot to log/ip7_unity/.

Walk the app on the phone in the printed order. The script saves a screen
when the picture changes and then stays still for ~1.2s.

Run:
    ./.venv/bin/python scripts/capture_ip7_unity.py
"""
import os
import sys
import time

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import config  # noqa: E402

UDID = os.environ.get("DEVICE_UDID") or "385e82401ffb88ee946698f951ae9b991beba9da"
OUT = os.path.join(config.LOG, os.environ.get("IP7_UNITY_DIR", "ip7_unity"))
BUNDLE = config.BUNDLE_ID

# Human walk order — fewer round-trips than the compare-tool ORDER.
STEPS = [
    ("MainMenu.png",
     "MAIN MENU — dismiss ATT (Allow) and any T&C, then stay on the menu"),
    ("StatsPage.png",
     "STATISTICS — tap Statistics, stay at the top of the page"),
    ("StatsResetBtn.png",
     "STATISTICS bottom — scroll down until Reset Statistics is visible"),
    ("OptionsPage.png",
     "OPTIONS — back to menu, tap Options"),
    ("HelpPage.png",
     "HELP — back to menu, tap Help (Introduction at the top)"),
    ("SpiderAboutPage.png",
     "ABOUT — back to menu, tap About"),
    ("SpiderFAQ.png",
     "FAQ — on About, tap frequently asked questions"),
    ("MoreGames.png",
     "MORE GAMES — back to menu, tap the gift / More Games icon"),
    ("choose_look_surface.png",
     "CHOOSE LOOK · Surface — back to menu, tap Choose Look"),
    ("choose_look_cards.png",
     "CHOOSE LOOK · Cards — tap the Cards tab"),
    ("DifficultyLevels.png",
     "DIFFICULTY — close Choose Look, tap Play"),
    ("Play.png",
     "GAME TABLE — start Easy (Yes to abandon if asked, No to review rules)"),
    ("InGameMenu.png",
     "IN-GAME MENU — tap the pause / menu control on the table"),
    ("VictoryScreen1.png",
     "VICTORY — complete a game (Dev Panel → Complete Game from the table)"),
    ("VictoryScreen2.png",
     "VICTORY · SCORE — tap through to the second victory / score screen"),
    ("LastScore.png",
     "LAST SCORE — back to the menu, open Last Score / Last Won Game Score"),
]


def _device():
    from tidevice import Device
    return Device(UDID)


def grab(dev, tries=4):
    last = None
    for attempt in range(tries):
        try:
            return dev.screenshot().convert("RGB")
        except Exception as exc:  # noqa: BLE001 — USB screenshot drops on iOS 15
            last = exc
            time.sleep(0.8 * (attempt + 1))
    raise last


def arr(image):
    return np.asarray(image, dtype=np.int16)


def diff_frac(a, b):
    if a is None or b is None or a.shape != b.shape:
        return 1.0
    return float(np.mean(np.abs(a - b) > 18))


def looks_like_splash(image):
    a = arr(image)
    # Launch icon on black: almost all pixels near black.
    return float((a.max(axis=2) < 40).mean()) > 0.88


def looks_like_att(image):
    a = arr(image)
    h, w = a.shape[:2]
    card = a[int(h * 0.28):int(h * 0.72), int(w * 0.08):int(w * 0.92)]
    white = np.all(card > 220, axis=2).mean()
    return white > 0.18


def save(image, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    image.save(path)
    print(f"  saved {name}  ({image.size[0]}x{image.size[1]})", flush=True)
    return path


def wait_settle(dev, previous=None, timeout=180, min_change=0.04):
    """Wait until the screen differs from previous, then two stable frames."""
    deadline = time.time() + timeout
    changed = previous is None
    last = previous
    stable = 0
    while time.time() < deadline:
        frame = grab(dev)
        cur = arr(frame)
        if looks_like_splash(frame) or looks_like_att(frame):
            last = cur
            changed = False
            stable = 0
            time.sleep(0.7)
            continue
        if not changed:
            if previous is None or diff_frac(cur, previous) >= min_change:
                changed = True
                stable = 0
            last = cur
            time.sleep(0.45)
            continue
        if diff_frac(cur, last) < 0.012:
            stable += 1
            if stable >= 3:
                return frame
        else:
            stable = 0
        last = cur
        time.sleep(0.4)
    raise TimeoutError("screen did not settle")


def main():
    os.makedirs(OUT, exist_ok=True)
    dev = _device()
    print(f"device {UDID}  ->  {OUT}", flush=True)
    print("Launching Spider…", flush=True)
    try:
        dev.app_start(BUNDLE)
    except Exception as exc:  # noqa: BLE001
        print(f"  launch note: {exc}", flush=True)
    time.sleep(3)

    print("\nOn the iPhone 7, walk this order. After each save, go to the next.\n",
          flush=True)
    last = None
    for name, hint in STEPS:
        dest = os.path.join(OUT, name)
        if os.path.isfile(dest) and "--fresh" not in sys.argv:
            print(f"  skip {name} (already captured)", flush=True)
            last = arr(Image.open(dest).convert("RGB"))
            continue
        print(f"→  {hint}", flush=True)
        frame = wait_settle(dev, previous=last, timeout=240)
        save(frame, name)
        last = arr(frame)

    menu = os.path.join(OUT, "MainMenu.png")
    icons = os.path.join(OUT, "more_games_icons.png")
    if os.path.isfile(menu) and not os.path.isfile(icons):
        Image.open(menu).save(icons)
        print("  copied MainMenu.png -> more_games_icons.png", flush=True)

    print("\nDone. Next:", flush=True)
    print("  IP7_UNITY_DIR=ip7_unity ./.venv/bin/python "
          "tests/compare_unity_ip7.py --report", flush=True)


if __name__ == "__main__":
    main()
