#!/usr/bin/env python3
"""Build-aware driver: run one functional test against BOTH the Obj-C and Unity
builds of Spider Solitaire.

A test is written once against this semantic API (launch_to_menu / open /
on_screen / back / ...). The driver detects which build is on the device and
resolves every action to that build's locators:

  * Obj-C  — the inherited image templates + flows.py helpers (the proven path
             from before the port).
  * Unity  — fixed screen coordinates + Unity-cropped screen anchors. Unity
             renders to an opaque view (no accessibility tree, so no Poco) and
             its buttons no longer match the Obj-C template crops, so we tap by
             coordinate and recognise screens with tight Unity title crops.

The build differences live in PROFILES; the tests never branch on build.

Detection order:
  1. BUILD=objc|unity environment override (use this in CI / to force a build).
  2. WDA accessibility-tree probe — Unity's tree is an opaque Application ->
     Window -> a few generic Other containers with no Button/StaticText
     elements; a UIKit/Obj-C build exposes named elements.
NOTE: the probe is validated against Unity (the only build currently installed).
When an Obj-C build is reinstalled, confirm it classifies as "objc" (it should,
via its UIKit elements) or just force BUILD=objc.

Currently wired for the menu + Options screen (tests/verifyOptions.py). Extend
PROFILES (and add Unity anchor crops in assets/) as more screens are ported.
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402
import flows  # noqa: E402
import helpers  # noqa: E402

# ── per-build locator profiles ────────────────────────────────────────
# A locator is (kind, value):  ("tpl", "<asset>") | ("coord", (x, y)).
# "menu_anchors": templates that reliably identify the main menu on that build
# (all must be present). "back": how to return to the menu from a sub-screen.
PROFILES = {
    "objc": {
        "menu_anchors": ["menu_play", "menu_options"],   # == flows.on_main_menu
        "controls": {"options": ("tpl", "menu_options")},
        "screens":  {"options": ("tpl", "screen_options")},
        "back": ("flows_back", None),
    },
    "unity": {
        "menu_anchors": ["menu_play", "menu_help"],       # still match on Unity
        "controls": {"options": ("coord", (631, 1089))},
        "screens":  {"options": ("tpl", "screen_options_unity")},
        "back": ("coord", (100, 82)),
    },
}


def detect_build() -> str:
    """Classify the foregrounded app as 'objc' or 'unity'.

    Call this with the Spider app already foregrounded (driver() does that) —
    the probe reads whatever is on screen, so probing the home screen or a
    system UI would misclassify.
    """
    override = os.environ.get("BUILD", "").strip().lower()
    if override in ("objc", "unity"):
        return override
    try:
        src = urllib.request.urlopen(
            config.WDA_URL + "/source?format=xml", timeout=12).read().decode()
        named = len(re.findall(
            r"XCUIElementType(?:Button|StaticText|Cell|TextField|Link|SearchField)", src))
        return "objc" if named >= 4 else "unity"
    except Exception:  # noqa: BLE001 — default to the build we know is installed
        return "unity"


class Driver:
    """Semantic, build-agnostic UI driver. Construct via driver()."""

    def __init__(self, build: str):
        self.build = build
        self.p = PROFILES[build]

    # ── semantic API (tests call these) ─────────────────────────
    def launch_to_menu(self):
        """Foreground the app on the main menu."""
        if self.build == "unity":
            return self._unity_goto_menu()
        flows.launch_to_menu()
        return self.on_menu()

    def on_menu(self, timeout: float = 6.0) -> bool:
        anchors = self.p["menu_anchors"]
        return (bool(flows.seen(anchors[0], timeout))
                and all(flows.exists(flows.T(a)) for a in anchors[1:]))

    def open(self, key: str):
        """Tap a main-menu control (e.g. 'options')."""
        self._act(self.p["controls"][key])
        time.sleep(2.0)                     # let the transition finish

    def on_screen(self, key: str, timeout: float = 6.0) -> bool:
        kind, val = self.p["screens"][key]
        if kind == "tpl":
            return bool(flows.seen(val, timeout))
        raise ValueError(f"unsupported screen locator: {kind}")

    def back(self) -> bool:
        """Return to the main menu; True once we're back on it."""
        kind, val = self.p["back"]
        if kind == "flows_back":
            return flows.back_to_menu()
        if kind == "coord":
            flows.tap_at(val)
            time.sleep(1.2)
            return self.on_menu()
        raise ValueError(f"unsupported back locator: {kind}")

    def shoot(self, name: str) -> str:
        return flows.shoot(name)

    # ── assertion sugar (raise via flows.expect) ────────────────
    def assert_on_menu(self, msg: str = "not on the main menu"):
        flows.expect(self.on_menu(), msg)

    def assert_off_menu(self, msg: str = "still on the main menu"):
        flows.expect(not self.on_menu(timeout=1.0), msg)

    def assert_screen(self, key: str, msg: str = None):
        flows.expect(self.on_screen(key), msg or f"'{key}' screen not detected")

    # ── internals ───────────────────────────────────────────────
    def _act(self, loc):
        kind, val = loc
        if kind == "coord":
            flows.tap_at(val)
        elif kind == "tpl":
            flows.tap(val)
        else:
            raise ValueError(f"unsupported control locator: {kind}")

    # Unity menu navigation: coordinate-based (its templates/on_main_menu are
    # unreliable). Mirrors tests/compare_unity.py's capture nav.
    def _unity_goto_menu(self) -> bool:
        flows.connect_device(config.DEVICE_URI)
        flows.dismiss_popups()
        for _ in range(3):
            if self.on_menu(1.5):
                return True
            flows.tap_at((100, 82))         # coord "back"; harmless on the menu
            time.sleep(1.2)
        return self._unity_cold_launch()

    def _unity_cold_launch(self) -> bool:
        sid = helpers.launch_app()
        time.sleep(1.5)
        self._terminate(sid)
        time.sleep(1.5)
        helpers.launch_app()                # fresh launch foregrounds to the menu
        time.sleep(3)
        flows.connect_device(config.DEVICE_URI)
        flows.dismiss_popups()
        return self.on_menu(8.0)

    @staticmethod
    def _terminate(sid: str):
        data = json.dumps({"bundleId": config.BUNDLE_ID}).encode()
        req = urllib.request.Request(
            config.WDA_URL + f"/session/{sid}/wda/apps/terminate",
            data=data, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=20)
        except Exception:  # noqa: BLE001 — best-effort kill
            pass


def driver() -> Driver:
    """Connect the device, foreground the app, detect the build, return a Driver.

    We foreground the app before detecting so the accessibility-tree probe reads
    the game's own view hierarchy (not the home screen / a system UI, which would
    look 'rich' and misclassify as Obj-C).
    """
    flows.connect_device(config.DEVICE_URI)
    helpers.launch_app()
    time.sleep(3)
    return Driver(detect_build())
