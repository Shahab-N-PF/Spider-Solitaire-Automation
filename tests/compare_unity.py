#!/usr/bin/env python3
"""Capture the Unity build's screens and diff them against the Obj-C baselines.

This is the pixel-fidelity check for the Objective-C -> Unity port. It walks the
Unity build to all ten baselined screens, screenshots each into log/, and runs
the exact-pixel comparison (visual.compare) against baselines/, which are the
Obj-C reference and are NEVER modified here. A large diff is the intended signal
(it's where the port still deviates), not a harness failure.

Why coordinate navigation: the Unity build renders its whole UI into an opaque
view with NO accessibility tree (Poco sees nothing), and its buttons no longer
match the Obj-C image templates. So we drive it by fixed screen coordinates,
which also keeps the driver independent of the very pixels we're measuring. If a
new Unity build moves things, re-shoot with tests/launch_and_shoot.py and update
the coordinates below.

Run:  ./.venv/bin/python tests/compare_unity.py [--report]
        --report also writes log/unity_compare.html (interactive wipe/fade report).
Prereqs: WDA up (scripts/wda.sh), iPhone unlocked.
Exit status: non-zero if any screen exceeds its visual.SPECS threshold.
"""
import base64
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import flows  # noqa: E402
import helpers  # noqa: E402
import visual  # noqa: E402
from airtest.core.api import touch  # noqa: E402

# ── Unity screen coordinates (portrait capture space, 828x1792) ───────
# Menu button centres: play/stats/help/about are the live template matches
# (those labels still match the Obj-C templates on Unity); options + the back
# button are tap-validated. more_games / choose_look are the left-column items.
MENU = {"play": (672, 806), "stats": (632, 971), "options": (631, 1089),
        "help": (596, 1246), "about": (637, 1398),
        "more_games": (150, 1225), "choose_look": (150, 1325)}
BACK = (100, 82)                 # sub-screen "back" (top-left)
LOOK_CARDS_TAB = (480, 550)      # Choose Look -> Cards tab
LOOK_CLOSE = (687, 582)          # Choose Look modal close (x)
PLAY_EASY = (660, 850)           # Play -> difficulty picker -> Easy
PLAY_RULES_NO = (260, 1005)      # "No" on the first-game "review the game rules?" dialog

# The ten baselined screens, in the order captured (Main Menu is shot once and
# compared under both MainMenu.png and more_games_icons.png — same screen).
COMPARE_ORDER = ["MainMenu", "more_games_icons", "StatsPage", "OptionsPage",
                 "HelpPage", "SpiderAboutPage", "MoreGames",
                 "choose_look_surface", "choose_look_cards", "Play"]


def at_menu(timeout=6.0) -> bool:
    """Reliable 'are we on the menu?' for Unity.

    Uses menu_play + menu_help, which still match the Unity rendering. We avoid
    on_main_menu()/menu_options here: the Options label is borderline on Unity,
    which is exactly what makes the template-based check unreliable.
    """
    return bool(flows.seen("menu_play", timeout)) and flows.exists(flows.T("menu_help"))


def _terminate(sid: str):
    data = json.dumps({"bundleId": config.BUNDLE_ID}).encode()
    req = urllib.request.Request(
        config.WDA_URL + f"/session/{sid}/wda/apps/terminate",
        data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:  # noqa: BLE001 — best-effort kill
        pass


def cold_launch() -> bool:
    """Terminate + relaunch to a clean menu (recovers from any stuck state)."""
    sid = helpers.launch_app()
    time.sleep(1.5)
    _terminate(sid)
    time.sleep(1.5)
    helpers.launch_app()            # fresh launch foregrounds to the menu
    time.sleep(3)
    flows.connect_device(config.DEVICE_URI)
    flows.dismiss_popups()
    return at_menu(8.0)


def goto_menu() -> bool:
    """Ensure we're on the menu: walk back with the coord back button, else cold."""
    flows.connect_device(config.DEVICE_URI)
    flows.dismiss_popups()
    for _ in range(3):
        if at_menu(1.5):
            return True
        touch(BACK)
        time.sleep(1.2)
    return cold_launch()


# ── per-screen capture (each assumes we start on the menu) ────────────
def cap_menu():
    time.sleep(2)                   # let the menu settle
    flows.shoot("MainMenu")
    flows.shoot("more_games_icons")  # same screen; the promo strip lives here
    return ["MainMenu", "more_games_icons"]


def _sub(anchor: str, shot: str):
    touch(MENU[anchor])
    time.sleep(2.5)
    flows.shoot(shot)
    touch(BACK)
    time.sleep(1.5)
    return [shot]


def cap_stats():   return _sub("stats", "StatsPage")
def cap_options(): return _sub("options", "OptionsPage")
def cap_help():    return _sub("help", "HelpPage")
def cap_about():   return _sub("about", "SpiderAboutPage")


def cap_more_games():
    touch(MENU["more_games"])
    time.sleep(3)
    flows.shoot("MoreGames")
    touch(BACK)
    time.sleep(1.5)
    return ["MoreGames"]


def cap_choose_look():
    touch(MENU["choose_look"])
    time.sleep(5)                   # let the Game Center "signed in" toast fade
    flows.shoot("choose_look_surface")
    touch(LOOK_CARDS_TAB)
    time.sleep(2.5)
    flows.shoot("choose_look_cards")
    touch(LOOK_CLOSE)               # the modal closes via x, not back
    time.sleep(1.5)
    return ["choose_look_surface", "choose_look_cards"]


def cap_play():
    touch(MENU["play"])
    time.sleep(2)
    touch(PLAY_EASY)                # fresh Easy deal (matches the Easy baseline)
    time.sleep(3)
    touch(PLAY_RULES_NO)            # dismiss the first-game "review the rules?" dialog;
    time.sleep(3)                   # a harmless empty-felt tap if the dialog isn't shown
    flows.shoot("Play")
    touch(BACK)
    time.sleep(1.5)
    return ["Play"]


SCREENS = [
    ("Main Menu + promo", cap_menu),
    ("Statistics", cap_stats),
    ("Options", cap_options),
    ("Help", cap_help),
    ("About", cap_about),
    ("More Games", cap_more_games),
    ("Choose Look", cap_choose_look),
    ("Play", cap_play),
]


def run(report: bool = False) -> int:
    flows.connect_device(config.DEVICE_URI)
    print("=== CAPTURE (Unity build) — coordinate navigation ===")
    for label, fn in SCREENS:
        if not goto_menu():
            print(f"  !! could not reach the menu before {label}; skipping")
            continue
        try:
            names = fn()
            print(f"  captured {label}: {', '.join(names)}")
        except Exception as e:  # noqa: BLE001 — one screen shouldn't sink the run
            print(f"  !! {label} capture failed: {e}")

    print("\n=== COMPARE Unity capture vs Obj-C baseline ===")
    fails = 0
    total = 0
    for name in COMPARE_ORDER:
        fn = name + ".png"
        spec = visual.SPECS.get(fn)
        if spec is None:
            continue
        total += 1
        r = visual.compare(fn, spec["ignore"], spec["max_diff"])
        dp = r["diff_pct"]
        dps = f"{dp:6.2f}%" if dp is not None else "   n/a"
        status = r["status"].upper()
        if r["status"] == "fail":
            fails += 1
        tail = f"  -> log/{os.path.basename(r['diff'])}" if r.get("diff") else ""
        print(f"  {name:20s} {dps}  (thr {spec['max_diff']*100:.1f}%)  {status}{tail}")
    print(f"\n  {total - fails}/{total} within threshold; {fails} differ from the Obj-C baseline")

    if report:
        sys.path.insert(0, os.path.join(config.ROOT, "scripts"))
        import gen_compare_report  # noqa: E402
        out = gen_compare_report.build()
        print(f"\n  report: {out}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run(report="--report" in sys.argv))
