"""Unity-build UI driver — the foundation of the Unity functional suite.

This is the Unity counterpart to flows.py (which drives the Obj-C build). It is
deliberately a SEPARATE module rather than a branch inside flows.py, because
almost nothing about locating a control is shared between the two renderers.

Why the Unity build needs its own driver
----------------------------------------
Unity draws the entire UI into one opaque view. There is no accessibility tree,
so Poco sees nothing and WDA reports a single anonymous element — element-based
automation is simply unavailable. That leaves pixels.

The pixel-fidelity tools (tests/compare_unity*.py) therefore drive Unity by fixed
coordinates, and for *them* that is the right call: a comparison must not locate
its targets using the very pixels it is measuring, or a real regression could
move a button and the harness would silently follow it.

Functional testing wants the opposite trade. Here we ask "does the button work?",
so finding the button by sight is not cheating — it is the assertion. Templates
cropped from Unity's OWN rendering (scripts/crop_unity_assets.py,
scripts/derive_unity_assets.py -> UNITY_ASSETS) let a test say "the Options
control is on screen" and tap wherever it actually is. That survives the layout
shifts between Unity builds that broke the hardcoded coordinates in
compare_unity.py, and it turns "did we land on the right screen?" into a real
check instead of an assumption.

Note the inherited assets/ templates are Obj-C crops and do NOT match Unity —
this module never uses them.

Conventions
-----------
  * Coordinates are in capture-pixel space (whatever snapshot() returns).
  * Locators are template names in config.UNITY_ASSETS.
  * seen() waits; find()/is_on() are single-shot.
  * find() is scale-aware, so ONE template set serves every 19.5:9 device.
  * Every helper that can fail returns a bool/None; tests turn those into
    failures with expect(), so messages stay in the test.
"""
import logging
import os
import time

import config
import helpers
from airtest.core.api import connect_device, snapshot, swipe, text, touch
from airtest.core.settings import Settings as ST

logging.getLogger("airtest").setLevel(logging.WARNING)

# Matching is done by find() below rather than by airtest, so these only affect
# any airtest call a test makes directly: template matching only (the keypoint
# fallback never helps at matching resolution and makes every negative check
# expensive), single-shot so callers own the waiting.
ST.CVSTRATEGY = ["tpl"]
ST.FIND_TIMEOUT_TMP = 0.5

DEFAULT_THRESH = 0.7

# Per-template threshold overrides. Only for templates that a screen-uniqueness
# check (scripts/verify_unity_assets.py) showed can collide:
#   look_cards_tab — the Help page's body text contains the word "Cards", which
#   scores ~0.71 against the tab. Its true match is ~0.99, so the bar is raised
#   well clear of the collision rather than the crop being made less legible.
#   in_game_menu — the top bar's "menu" word: SHARED CHROME (the Stats page,
#   Help page and victory screen all carry it), so it is no longer the table
#   anchor — see SCREENS["table"]. Its only job now is to be FOUND so the drawer
#   can be tapped, from a screen we already know is the table. The crop was
#   re-cut tight to the glyphs (see crop_unity_assets.py) which opened a real
#   gap: worst true match 0.754 on an iPhone 16 Pro, worst non-table 0.660.
#   0.72 sits centrally in that gap.
#   last_score_next — the Last Score screen's forward arrow. A plain triangle
#   with no internal detail, so it correlates with all sorts of unrelated art:
#   0.685 on the About screen and 0.655 on the game table, against 1.000 on its
#   own screen. That is 0.015 of daylight under the default — not a threshold, a
#   coin toss. 0.85 puts the bar in the middle of the real gap (worst true match
#   0.941, on the victory screen's identical stepper).
THRESH = {
    "look_cards_tab": 0.88,
    "in_game_menu": 0.72,
    "last_score_next": 0.85,
}


# NOTE: there is deliberately no T()/Template() helper here any more. Handing a
# Template to airtest matches it at ONE scale — the size it was cropped at — which
# silently fails on any device other than the one it came from. Everything goes
# through find() instead, which rescales for the attached device. See the
# device-independent matching section below.


def have(name: str) -> bool:
    """True if the template file exists (not whether it's on screen)."""
    return os.path.exists(os.path.join(config.UNITY_ASSETS, name + ".png"))


# ── screen model ──────────────────────────────────────────────────
# Semantic screen name -> the anchor that proves we are on it. An anchor is a
# title/heading unique to that screen, so "did the tap open the right screen?"
# is a positive check rather than "the previous screen went away".
SCREENS = {
    "options":    "screen_options",
    "stats":      "screen_stats",
    "help":       "screen_help",
    "about":      "screen_about",
    "more_games": "screen_more_games",
    "surface":    "screen_surface",     # Choose Look, Surface tab
    "cards":      "screen_cards",       # Choose Look, Cards tab
    "difficulty": "difficulty_easy",    # the Play difficulty picker
    # "tap to undo", the table's own bottom-left control — NOT the top bar's
    # "menu" word, which was the anchor until it proved unusable: "menu" is
    # shared chrome (Stats, Help and the victory screen all carry it) and it sits
    # on the felt, so a Choose Look surface change moves its score too. On the
    # iPhone 16 Pro with a blue surface it scored 0.794 on a REAL table, below
    # the 0.827 it reaches on screens that are NOT a table — no threshold can
    # separate those. tap_undo is table-only and scored 0.979 in the same frame.
    "table":      "tap_undo",
    "ingame_menu": "ingame_replay",     # the in-game menu drawer is open
    "victory":    "screen_victory",
    # "Last Won Game Score", reached from the difficulty picker's bottom-left
    # label. Anchored on its HEADER because the rest of the screen is the same
    # ranking view the victory screen draws: screen_victory itself matches here
    # (0.99), as do victory_ranking / victory_leaderboards / victory_achieve. So
    # at_screen("victory") is TRUE on this screen — check "last_score" first if
    # you need to tell the two apart.
    "last_score": "screen_last_score",
}

# Main-menu controls (all are also their own on-screen proof).
MENU_ITEMS = ("menu_play", "menu_stats", "menu_options", "menu_help",
              "menu_about", "more_games", "choose_look")

DIFFICULTIES = ("easy", "medium", "hard", "bold", "expert")


# ── primitives ────────────────────────────────────────────────────
def connect():
    connect_device(config.DEVICE_URI)


def sleep(sec: float):
    time.sleep(sec)


def expect(cond, msg: str):
    if not cond:
        raise AssertionError(msg)


# ── device-independent template matching ──────────────────────────
# ONE template set serves every phone in the 19.5:9 family. The crops in
# UNITY_ASSETS were cut from captures REF_WIDTH px wide; before matching, each is
# resized by (this device's capture width / REF_WIDTH).
#
# That works because Unity scales its whole UI by width across these devices —
# measured, not assumed. Cross-matching every template between an iPhone 11 (828)
# and an iPhone 14 Pro Max (1290) capture of the SAME screen: 49/49 match, median
# score 0.978, and the winning scale clusters at 0.645 (sd 0.003) against a
# predicted width ratio of 0.642. The ~0.5% gap between predicted and actual is
# exactly why a narrow sweep is kept around the prediction instead of trusting
# the ratio outright.
#
# Covered by one set: iPhone 11 (828x1792), iPhone 14 Pro Max (1290x2796),
# iPhone 16 Pro (1206x2622) — all ~19.5:9, so the scale is a pure width ratio.
# NOT covered: the iPhone 7 (750x1334, 16:9), whose UI genuinely reflows rather
# than scaling; it keeps its own per-device set.
REF_WIDTH = int(os.environ.get("UNITY_REF_WIDTH", "828"))

# ...but the app draws in TWO regimes, and they scale differently.
#
# Spider's confirmation dialogs are native iOS alerts, not Unity content: SF
# font, translucent rounded card, system button pills. Those are laid out in
# POINTS, so between an @2x phone and an @3x phone they scale by the point
# density (3/2 = 1.500), while Unity's own artwork scales by the width ratio
# (1206/828 = 1.4565 on the iPhone 16 Pro). Only ~3% apart — and that 3% is
# enough to miss: on the iPhone 16 Pro `prompt_abandon` peaked at 0.962 @1.500
# but only 0.694 within the width-based sweep, so the abandon prompt went
# unrecognised and was answered "No", which cancelled every deal in the suite.
#
# Hence a per-template basis rather than one wider sweep, which would just
# reintroduce the false positives the tight sweep exists to prevent.
REF_POINT_SCALE = float(os.environ.get("UNITY_REF_POINT_SCALE", "2.0"))

# Templates cropped from native iOS UI. Verified on the iPhone 16 Pro: each
# peaks at exactly the point-density ratio, not the width ratio.
# Game Center is the third regime and belongs here too: the sheet Spider
# presents for leaderboards is Apple's own UI, drawn out of process — WDA sees
# only anonymous XCUIElementTypeOther over it, exactly like the ATT prompt — so
# it is laid out in points and must be matched as an image.
NATIVE_UI = {"prompt_abandon", "dialog_yes", "dialog_no", "prompt_tip", "tip_ok",
             "att_prompt", "att_deny", "gc_leaderboards", "gc_achievements",
             "gc_back"}

_POINT_SCALE = None


def point_scale() -> float:
    """Capture pixels per WDA point on this device (2.0 @2x, 3.0 @3x). Cached."""
    global _POINT_SCALE
    if _POINT_SCALE is None:
        try:
            _POINT_SCALE = _point_scale()
        except Exception:  # noqa: BLE001 — no WDA session (offline tools)
            _POINT_SCALE = screen_size()[0] / float(REF_WIDTH) * REF_POINT_SCALE
    return _POINT_SCALE


def template_scale(name: str) -> float:
    """The resize factor for <name> on this device, per its rendering regime."""
    if name in NATIVE_UI:
        return point_scale() / REF_POINT_SCALE
    return screen_size()[0] / float(REF_WIDTH)

# Multipliers applied to the predicted scale, tried in this order with an early
# exit. 1.0 first means the common case costs a single matchTemplate — the sweep
# only runs when the prediction alone does not clear the threshold.
#
# Kept DELIBERATELY tight. Every extra scale is another chance for a wrong screen
# to cross the threshold, and that is not hypothetical: at +/-3% the "menu" word
# in in_game_menu started matching the Stats and Help pages (0.759 / 0.712) that
# it scores only 0.684 / 0.659 against at native scale. Measured false matches
# across the five weak screens: +/-3% -> 3, +/-1% -> 1, single scale -> 0.
# +/-1% is still 2-3x the observed prediction error (the true scale lands within
# ~0.5% of the width ratio, sd 0.003-0.005), so it buys tolerance without
# meaningfully widening the door.
_SCALE_SWEEP = (1.0, 0.99, 1.01)

# If even the best sweep candidate is this far below threshold, a few percent of
# rescaling was never going to rescue it — stop early rather than finish the
# sweep. Keeps negative checks (lost() probes nine landmarks) affordable.
_HOPELESS = 0.15

_TPL_CACHE = {}


def _tpl_image(name: str):
    """Load and cache a template as a BGR array."""
    import cv2
    if name not in _TPL_CACHE:
        _TPL_CACHE[name] = cv2.imread(
            os.path.join(config.UNITY_ASSETS, name + ".png"))
    return _TPL_CACHE[name]


def _screen_image():
    """Current screen as a BGR array (no file written)."""
    from airtest.core.helper import G
    return G.DEVICE.snapshot()


def device_scale() -> float:
    """Width-ratio scale for Unity-drawn content (see template_scale()).

    1.0 on the iPhone 11 the crops came from, ~1.56 on an iPhone 14 Pro Max,
    ~1.46 on an iPhone 16 Pro.
    """
    return screen_size()[0] / float(REF_WIDTH)


def find(name: str, threshold: float = None, screen=None):
    """Match position (x, y) of <name> right now, or None.

    Scale-aware: the template is resized for the attached device before
    matching, so the same crop works on any phone in the family above. Pass
    `screen` to match several templates against one already-captured frame.
    """
    import cv2
    if not have(name):
        return None
    tpl = _tpl_image(name)
    if tpl is None:
        return None
    img = _screen_image() if screen is None else screen
    thr = threshold if threshold is not None else THRESH.get(name, DEFAULT_THRESH)
    base = template_scale(name)

    best = -1.0
    for k in _SCALE_SWEEP:
        s = base * k
        w, h = int(round(tpl.shape[1] * s)), int(round(tpl.shape[0] * s))
        if w < 8 or h < 8 or w > img.shape[1] or h > img.shape[0]:
            continue
        # INTER_AREA is the right filter for shrinking, CUBIC for enlarging;
        # using the wrong one costs real match score on text-heavy crops.
        resized = tpl if s == 1.0 else cv2.resize(
            tpl, (w, h),
            interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        res = cv2.matchTemplate(img, resized, cv2.TM_CCOEFF_NORMED)
        _, val, _, loc = cv2.minMaxLoc(res)
        if val >= thr:
            return (int(loc[0] + w / 2), int(loc[1] + h / 2))
        best = max(best, val)
        if best < thr - _HOPELESS:
            break
    return None


def is_on(name: str, threshold: float = None) -> bool:
    return find(name, threshold) is not None


def seen(name: str, timeout: float = 8.0, threshold: float = None) -> bool:
    """Poll until <name> is on screen or `timeout` elapses."""
    deadline = time.time() + timeout
    while True:
        if is_on(name, threshold):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.2)


def tap(name: str, timeout: float = 8.0, settle: float = 1.5,
        threshold: float = None) -> bool:
    """Wait for <name>, tap where it actually is, settle. False if never seen.

    Taps the matched POSITION rather than handing the Template back to airtest,
    whose matching is single-scale and would miss on any device the crops were
    not cut from.
    """
    if not seen(name, timeout, threshold):
        return False
    pos = find(name, threshold)
    if pos is None:                 # matched a moment ago, gone now
        return False
    touch(pos)
    time.sleep(settle)
    return True


def tap_at(pos, settle: float = 1.2):
    """Tap a raw capture-space coordinate."""
    touch(pos)
    time.sleep(settle)


def _point_scale() -> float:
    """Capture pixels per WDA point (2.0 on a @2x device, 3.0 on @3x)."""
    import json
    import urllib.request
    sid = helpers.current_session()
    size = json.load(urllib.request.urlopen(
        config.WDA_URL + f"/session/{sid}/window/size", timeout=15))["value"]
    return screen_size()[0] / float(size["width"])


def rapid_tap(pos, times: int = 10, gap_ms: int = 45, settle: float = 1.5) -> bool:
    """Tap one point `times` in genuinely rapid succession.

    For hidden debug gestures that count N *rapid* taps. This cannot be done by
    looping a normal tap: each airtest touch is its own WDA round trip, measured
    at ~510 ms on this rig, so ten of them span >5 s — far outside any "10 rapid
    taps" detection window. A gesture would then look absent when it is only
    being driven too slowly.

    So the whole burst is sent as ONE W3C Actions request and executed on-device
    back-to-back (~70 ms per tap). WDA actions take POINTS, not capture pixels,
    hence the scale conversion. Falls back to the slow loop if the endpoint
    fails, returning False so a caller can tell the burst wasn't really rapid.
    """
    import json
    import urllib.request
    try:
        scale = _point_scale()
        x, y = pos[0] / scale, pos[1] / scale
        seq = [{"type": "pointerMove", "duration": 0, "x": int(x), "y": int(y)}]
        for _ in range(times):
            seq += [{"type": "pointerDown", "button": 0},
                    {"type": "pause", "duration": 25},
                    {"type": "pointerUp", "button": 0},
                    {"type": "pause", "duration": gap_ms}]
        body = json.dumps({"actions": [{
            "type": "pointer", "id": "finger1",
            "parameters": {"pointerType": "touch"}, "actions": seq}]}).encode()
        sid = helpers.current_session()
        req = urllib.request.Request(
            config.WDA_URL + f"/session/{sid}/actions", data=body,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30)
        time.sleep(settle)
        return True
    except Exception:  # noqa: BLE001 — fall back, but say the burst was slow
        touch(pos, times=times)
        time.sleep(settle)
        return False


def type_text(content: str, settle: float = 1.5):
    """Type into the focused field via the device keyboard (WDA)."""
    text(content, enter=False)
    time.sleep(settle)


def tap_near(name: str, dx: int = 0, dy: int = 0, settle: float = 1.2,
             timeout: float = 6.0) -> bool:
    """Tap at an offset from where <name> matched.

    For controls with no distinctive art of their own that sit at a fixed offset
    from a label — the game table's undo/lower/hints targets live directly under
    their captions. Anchoring to the caption keeps this working when the layout
    moves between builds, which a hardcoded point would not.
    """
    if not seen(name, timeout):
        return False
    x, y = find(name)
    touch((x + dx, y + dy))
    time.sleep(settle)
    return True


def shoot(name: str) -> str:
    """Screenshot into log/<name>.png and return the path."""
    fn = name if name.endswith(".png") else name + ".png"
    out = os.path.join(config.LOG, fn)
    os.makedirs(config.LOG, exist_ok=True)
    snapshot(filename=out)
    return out


_SIZE = None


def screen_size():
    """(w, h) of the capture space. Cached — it costs a screenshot to learn."""
    global _SIZE
    if _SIZE is None:
        from PIL import Image
        _SIZE = Image.open(shoot("_size_probe")).size
    return _SIZE


def scroll(down: bool = True, frac: float = 0.45, duration: float = 0.4):
    """Swipe inside the content band to scroll a long screen."""
    w, h = screen_size()
    x = w // 2
    top, bottom = int(h * 0.30), int(h * 0.78)
    span = int(h * frac)
    if down:
        swipe((x, bottom), (x, bottom - span), duration=duration)
    else:
        swipe((x, top), (x, top + span), duration=duration)
    time.sleep(0.8)


def scroll_to(name: str, max_swipes: int = 10, down: bool = True) -> bool:
    """Scroll until <name> is on screen. True if found."""
    for _ in range(max_swipes):
        if is_on(name):
            return True
        scroll(down=down)
    return is_on(name)


# ── app lifecycle ─────────────────────────────────────────────────
def launch(settle: float = 4.0, force: bool = False):
    """Foreground the app via WDA (never airtest start_app — see CLAUDE.md).

    force=False ATTACHES to a running app instead of restarting it, so in-app
    state survives between tests (see helpers.launch_app). force=True restarts.
    """
    if not config.bundle_id_is_set():
        raise RuntimeError("BUNDLE_ID is not set")
    sid = helpers.launch_app(force=force)
    time.sleep(settle)
    connect()
    return sid


def active_app() -> str:
    """Bundle id of the app in the FOREGROUND, or "" if WDA will not say.

    The only way to tell "the tap opened another app" from "the tap did nothing
    but the screen changed" — image matching cannot see which app it is looking
    at. Used to check that the promo icons really hand off to the App Store.
    """
    import json
    import urllib.request
    sid = helpers.current_session()
    paths = [f"/session/{sid}/wda/activeAppInfo"] if sid else []
    paths.append("/wda/activeAppInfo")
    for p in paths:
        try:
            value = json.load(urllib.request.urlopen(
                config.WDA_URL + p, timeout=8))["value"]
            return value.get("bundleId") or ""
        except Exception:  # noqa: BLE001
            continue
    return ""


def in_app() -> bool:
    """True when Spider itself is the foreground app."""
    return active_app() == config.BUNDLE_ID


def resume(settle: float = 2.5) -> bool:
    """Bring Spider back to the front WITHOUT restarting it.

    For returning from somewhere iOS sent us — the App Store opened by a promo
    icon, say. Deliberately not terminate+relaunch: that would throw away the
    in-app state the rest of the run depends on (a dealt game, an unlocked Dev
    Panel). Verified on device: leave to the App Store and resume, and the Dev
    Panel button is still showing.
    """
    launch(settle=settle, force=False)
    return in_app()


def terminate(sid: str = None):
    """Best-effort kill, so the next launch is cold."""
    import json
    import urllib.request
    sid = sid or helpers.current_session()
    if not sid:
        return
    data = json.dumps({"bundleId": config.BUNDLE_ID}).encode()
    req = urllib.request.Request(
        config.WDA_URL + f"/session/{sid}/wda/apps/terminate",
        data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:  # noqa: BLE001
        pass


def cold_launch() -> bool:
    """Terminate + relaunch to a clean menu. The recovery of last resort.

    This is the one path that deliberately throws in-app state away (including
    any Dev Panel unlock), so it forces the relaunch.
    """
    sid = helpers.launch_app()
    time.sleep(1.5)
    terminate(sid)
    time.sleep(1.5)
    launch(force=True)
    clear_overlays()
    return on_menu(10.0)


# ── overlays: system alerts, in-app dialogs, interstitial ads ─────
# Alerts that gate a FRESH INSTALL and must be cleared before any test can run.
# Matched against the alert's own text (lowercased, substring), because that is
# what identifies it — never by position, and never by "some alert is up".
FIRST_LAUNCH_GATES = ("terms & conditions", "terms and conditions",
                      "must agree", "privacy policy")


def clear_overlays(rounds: int = 6) -> int:
    """Dismiss whatever is covering the UI. Returns how many were cleared.

    Three kinds, in order:

    1. The App Tracking Transparency prompt, by IMAGE. It is presented out of
       process, so the session's /alert/* endpoints 404 on it even though it is
       plainly on screen (helpers has the measurement). It is answered "Ask App
       Not to Track" — declining grants nothing, and the cross-promo content the
       tests look at does not depend on it.
    2. A first-launch gate alert, by its TEXT (FIRST_LAUNCH_GATES) — currently
       the Terms & Conditions / Privacy Policy notice, which has a single
       "Continue" button.
    3. An interstitial cross-promo ad (these appear when the device is online).

    Only alerts positively recognised as gates are accepted. The game's own
    confirmations are WDA-visible alerts too, and the right answer depends on
    which one it is (abandon wants Yes, the rules offer wants No), so anything
    unrecognised is left for settle_prompts() / answer_dialog() to judge.

    Both gates are once per install — but every TestFlight build is a fresh
    install, so the first run on each new build hits them.
    """
    cleared = 0
    sid = helpers.current_session()
    for _ in range(rounds):
        did = False
        if is_on("att_prompt"):                 # image-only; WDA cannot see it
            did = tap("att_deny", settle=1.5)
        if not did and sid:
            text = helpers.alert_text(sid).lower()
            if text and any(g in text for g in FIRST_LAUNCH_GATES):
                buttons = helpers.alert_buttons(sid)     # [] on WDA 15 -> default
                did = helpers.alert_tap(
                    sid, helpers.positive_button(buttons) if buttons else None)
        if not did and dismiss_ad(timeout=0.4):
            did = True
        if not did:
            break
        cleared += 1
        time.sleep(0.8)
    return cleared


AD_CLOSERS = ("ad_store_close", "ad_close")


def dismiss_ad(timeout: float = 1.5) -> bool:
    """Close ONE layer of ad if a known close control is showing.

    "One layer" is deliberate. Measured on build 353: leaving a game plays a
    video interstitial, the video auto-opens a StoreKit product sheet at its end
    with no tap from us, and closing that sheet starts a further playable ad. So
    a single close is not the same as "back in the game" — callers must loop and
    keep a time budget (see ad_free()).

    Only known-safe controls are tapped: ad_store_close (the X on the in-app
    StoreKit sheet, which sits on plain white and matches cleanly) and ad_close
    if a crop exists for this build. Never a guessed position — a close button
    moves with the creative and a miss taps the ad itself.
    """
    for name in AD_CLOSERS:
        if have(name) and seen(name, timeout=timeout):
            if tap(name, settle=1.5):
                return True
    return False


def ad_free(budget: float = 90.0) -> bool:
    """Clear ads until Spider's own UI is back, or the budget runs out.

    Returns True if we ended up on something recognisable. Ads chain, and some
    layers have no close control for a while, so this alternates "close what is
    closable" with "wait for the creative to finish".
    """
    deadline = time.time() + budget
    while time.time() < deadline:
        if not lost(timeout=1.0):
            return True
        if not dismiss_ad(timeout=1.0):
            time.sleep(2.0)
    return not lost(timeout=1.5)


# Anchors that between them appear on every screen of the app. If NONE of these
# match, we aren't looking at Spider at all.
_LANDMARKS = ("menu_play", "back_bar", "back_game", "back_promo", "in_game_menu",
              "ingame_replay", "look_close", "dialog_no", "screen_more_games",
              # Added after build 363 broke back_game on About: that crop was the
              # ONLY landmark there, so lost() began reporting a healthy About
              # screen as "an ad ate it" — and lost()'s handler relaunches the
              # app. A screen whose sole landmark is a back control is one stale
              # crop away from a silent restart, so About and the difficulty
              # picker each get an anchor of their own.
              "about_back", "stats_back", "difficulty_easy")


def lost(timeout: float = 2.0) -> bool:
    """True when nothing we recognise is on screen.

    In practice this means a full-screen cross-promo interstitial has taken
    over: this device is online, and FingerArts pops interstitials on screen
    transitions, so any tap can be answered by an ad instead of the expected
    screen. Distinguishing "an ad intervened" from "the control is broken"
    matters — the first deserves a retry, the second must fail.
    """
    if seen(_LANDMARKS[0], timeout=timeout):
        return False
    return not any(is_on(a) for a in _LANDMARKS[1:])


def recover(to_menu_after: bool = True) -> bool:
    """Get back into a known state after an interstitial (or any wedge).

    Relaunching is deliberate: an interstitial's close button moves with the ad
    creative, so hunting for it risks tapping the ad itself and being thrown into
    the App Store. Terminating and relaunching always lands back in Spider.
    """
    cold_launch()
    return on_menu(8.0) if to_menu_after else True


# ── in-app Yes/No dialogs ─────────────────────────────────────────
# Spider pops two look-alike confirmations with OPPOSITE correct answers:
#   "Are you sure you want to abandon the currently paused game?"  -> Yes
#   "Would you like to review the game rules before to play?"      -> No
# They share geometry, so answering by position alone is a coin flip.
#
# These are real UIAlertControllers, so WDA can READ them (/alert/text) and
# ANSWER them by button name — and that is the primary path here, because
# matching them as images is genuinely fragile: iOS renders them TRANSLUCENT, so
# a crop bakes in whatever was behind the alert at capture time. Measured on the
# iPhone 11 (build 353) with the abandon prompt plainly on screen and the crops
# taken from that very device: prompt_abandon 0.188, dialog_yes 0.311,
# dialog_no 0.329 — all far below 0.70, because the templates were cut over the
# game table and this one sat over the difficulty picker. WDA read the same
# alert's text exactly. Templates stay as the fallback for anything WDA cannot
# see (it is blind to out-of-process alerts — see clear_overlays).
ABANDON_TEXT = "abandon"
RULES_TEXT = "review the game rules"


def alert_now() -> str:
    """Text of the WDA-visible alert, or "" — the reliable presence check."""
    sid = helpers.current_session()
    return helpers.alert_text(sid) if sid else ""


def dialog_up(timeout: float = 1.0) -> bool:
    if alert_now():
        return True
    return seen("dialog_no", timeout=timeout) or seen("dialog_yes", timeout=0.3)


def answer_dialog(yes: bool, timeout: float = 4.0) -> bool:
    """Answer Yes/No on whatever confirmation is showing. False if none is up."""
    sid = helpers.current_session()
    if sid and helpers.alert_text(sid):
        if helpers.alert_tap(sid, "Yes" if yes else "No"):
            time.sleep(1.5)
            return True
    key = "dialog_yes" if yes else "dialog_no"
    return tap(key, timeout=timeout, settle=1.5)


def settle_prompts(max_rounds: int = 4) -> list:
    """Answer the known game dialogs correctly; return what was handled.

    Abandoning a paused game is what a test that asked for a fresh deal wants,
    and the rules tour is not — so Yes and No respectively.

    A third kind also lands on the table: a "Did you know?" tip with OK / Show Me
    (not Yes/No). It is answered OK — "Show Me" navigates away to Options — and
    it is checked FIRST, because it blocks taps on everything underneath it until
    it is dismissed.

    Classification prefers the alert's own TEXT (read over WDA), which names the
    dialog exactly. Only if WDA cannot see it does this fall back to the image
    anchor, where the abandon prompt is identified positively and anything else
    is taken to be the rules offer (the only other confirmation in this flow).
    """
    handled = []
    for _ in range(max_rounds):
        if is_on("prompt_tip"):             # tip card, OK / Show Me
            if tap("tip_ok", settle=1.2):
                handled.append("tip:ok")
                continue
        # WAIT for a dialog to render, THEN classify it. The order matters: an
        # earlier version tested prompt_abandon single-shot first and only then
        # waited, so a prompt that had not finished drawing fell through to the
        # fallback and was answered No — declining to abandon, which silently
        # cancels the deal and leaves the picker up. That is exactly how it
        # failed on the iPhone 16 Pro: every "did not reach the game table".
        if dialog_up(timeout=2.0):
            text = alert_now().lower()
            if text:                        # WDA can read it: no guessing
                if ABANDON_TEXT in text:
                    if answer_dialog(True):
                        handled.append("abandon:yes")
                        continue
                elif RULES_TEXT in text:
                    if answer_dialog(False):
                        handled.append("rules:no")
                        continue
                else:                       # unknown alert — decline, don't guess Yes
                    if answer_dialog(False):
                        handled.append(f"other:no ({text[:40]})")
                        continue
            if is_on("prompt_abandon"):     # image fallback
                if answer_dialog(True):
                    handled.append("abandon:yes")
                    continue
            if answer_dialog(False):
                handled.append("rules:no")
                continue
        break
    return handled


# ── navigation ────────────────────────────────────────────────────
def on_menu(timeout: float = 6.0) -> bool:
    """True when the main menu is up AND nothing is covering it.

    The Choose Look modal only covers the middle of the menu — the menu labels
    stay visible (and matchable) behind it, which scripts/verify_unity_assets.py
    flagged. So "the menu is visible" is not the same as "we are ON the menu";
    the modal has to be explicitly ruled out or a test could tap a menu item
    that is not actually reachable.
    """
    if not seen("menu_play", timeout):
        return False
    if is_on("look_close"):             # Choose Look modal is over the menu
        return False
    return is_on("menu_help")


def at_screen(key: str, timeout: float = 6.0) -> bool:
    anchor = SCREENS.get(key)
    if anchor is None:
        raise ValueError(f"unknown screen: {key}")
    return seen(anchor, timeout)


def back(settle: float = 1.5) -> bool:
    """Tap whichever 'back' control is on screen (each screen styles its own)."""
    for anchor in ("back_bar", "back_game", "back_promo", "about_back",
                   "stats_back"):
        if have(anchor) and is_on(anchor):
            return tap(anchor, timeout=1.0, settle=settle)
    return False


def to_menu(max_steps: int = 6) -> bool:
    """Walk back to the main menu without relaunching. True once there."""
    for _ in range(max_steps):
        if on_menu(timeout=1.2):
            return True
        if dismiss_ad(timeout=0.4):
            continue
        if is_on("look_close"):         # the modal closes via x, not back
            tap("look_close", timeout=1.0, settle=1.0)
            continue
        # The difficulty picker carries NO back control of any kind — matching
        # every template against a capture of it turns up the five level labels,
        # "LAST SCORE" and the logo, and nothing else. Its way out is the Spider
        # LOGO, which swaps the difficulty arc back for the menu arc.
        #
        # Without this branch to_menu() simply fails on the picker, and its
        # caller launch_to_menu() answers a failed to_menu() by COLD-LAUNCHING —
        # so any test that ended on the picker silently restarted the app and
        # took the Dev Panel unlock down with it. menu_logo is safe to use here:
        # it matches only the menu and picker frames (checked against every
        # capture in log/unity_screens), and on_menu() has already been ruled out
        # at the top of this loop.
        if is_on("difficulty_easy"):
            tap("menu_logo", timeout=1.0, settle=1.5)
            continue
        if dialog_up(timeout=0.4):      # a stray confirmation blocks navigation
            answer_dialog(False)
            continue
        if not back():
            if lost(timeout=1.0):       # an interstitial ate the screen
                return recover()
            break
    return on_menu(timeout=2.0)


def launch_to_menu(force: bool = False) -> bool:
    """Ensure the app is foregrounded on a clean main menu.

    force=True restarts the app first — use it when a test's premise is a fresh
    app state (openDebugTools asserts the Dev Panel button is hidden until its
    gesture reveals it, which is only true after a restart).
    """
    launch(force=force)
    clear_overlays()
    if to_menu():
        return True
    # First-launch gates arrive in sequence and not instantly (ATT, then Terms &
    # Conditions on the following launch), so one immediate sweep can land in the
    # gap between them and see a clear screen that is about to be covered.
    time.sleep(2.5)
    if clear_overlays() and to_menu():
        return True
    ok = cold_launch()
    if not ok:
        print(f"  [launch_to_menu] still not on the menu — {blocking()}")
    return ok


def blocking() -> str:
    """Best-effort description of what is covering the screen, for failure text."""
    if is_on("att_prompt"):
        return "the App Tracking Transparency prompt is up (image-matched)"
    sid = helpers.current_session()
    text = helpers.alert_text(sid) if sid else ""
    if text:
        return f"a native alert is up: {text!r}"
    return "no alert or tracking prompt detected"


def open_menu_item(name: str, settle: float = 2.5) -> bool:
    """Tap a main-menu control by template name (e.g. 'menu_options')."""
    if not tap(name, settle=settle):
        return False
    return True


def visit_sub_screen(control: str, screen: str, shot_name: str) -> str:
    """Open a main-menu sub-screen, prove we're on it, capture it, come back.

    Checks three things, because "the menu went away" proves nothing on its own:
    a positive anchor unique to the destination is showing (we opened the RIGHT
    screen), the menu is genuinely gone (we actually navigated), and back returns
    to the menu (the screen isn't a dead end). Returns the capture path.
    """
    expect(launch_to_menu(), f"[{screen}] could not reach the main menu")
    expect(tap(control, settle=2.5), f"[{screen}] menu control not found: {control}")
    expect(at_screen(screen, timeout=8.0),
           f"[{screen}] tapping {control} did not open the {screen} screen "
           f"(anchor '{SCREENS[screen]}' not found)")
    expect(not on_menu(timeout=1.0),
           f"[{screen}] tapping {control} did not leave the main menu")
    shot = shoot(shot_name)
    expect(to_menu(), f"[{screen}] could not get back to the main menu")
    return shot


# ── Options screen: toggles and sliders ───────────────────────────
# Every row on the Options page is <icon> <label> <control>, and there are
# exactly two kinds of control:
#
#   toggle  a pill with a knob — knob LEFT is off, knob RIGHT is on
#   slider  a track with a knob, with "-" and "+" marking the ends below it
#
# Both are read the same way: find the row by its LABEL template, then look for
# the white knob in the control column beside it. That is the only state these
# controls publish — Unity exposes no accessibility tree, so there is no boolean
# to query and no value to read. The knob's position IS the setting.
#
# Reading it (rather than only diffing pixels before/after) is what turns
# "something on screen changed" into "the toggle was ON, I tapped it, it is now
# OFF" — a claim a dead control, a passing animation or an ad cannot satisfy.
#
# Geometry measured off an iPhone 11 capture (828x1792) and stored as fractions
# of the screen, so it rescales with the templates. All four sliders and all
# eight toggles share one column, verified against both Options captures:
#   track 513-757 px, toggle pill 602-734 px, "-" 527, "+" 738, marks +43 px.
OPT_TRACK_L = 0.6196        # slider track, left end
OPT_TRACK_R = 0.9142        # slider track, right end
OPT_PILL_C = 0.8068         # toggle pill centre — knob right of it means ON
OPT_MINUS_X = 0.6365        # the "-" end mark under a slider — a LABEL, not a
OPT_PLUS_X = 0.8913         # button, and likewise "+" (see slider_drag's note)
OPT_MARKS_DY = 0.0240       # the end-mark row, below the control's own centre
OPT_ROW_BAND = 0.022        # how far either side of a label to hunt the knob

# Every row of the Options page, in page order, with the control it carries.
# All twelve stay listed even though verifyOptions now drives only four of them:
# opt_row() reads this ORDER to decide which way to scroll for a target, so a
# trimmed list would make navigation worse, not leaner. It is also the page model
# a full-inventory check would use again (see opt_scan).
OPT_ROWS = (
    ("opt_applause",       "slider", "sounds"),
    ("opt_effects",        "slider", "sounds"),
    ("opt_auto_mute",      "toggle", "sounds"),
    ("opt_card_spacing",   "toggle", "cards"),
    ("opt_card_bouncing",  "toggle", "cards"),
    ("opt_card_lowering",  "slider", "interface"),
    ("opt_status_bar",     "toggle", "interface"),
    ("opt_card_messages",  "toggle", "interface"),
    ("opt_brightness",     "slider", "interface"),
    ("opt_rich_features",  "toggle", "interface"),
    ("opt_use_hearts",     "toggle", "interface"),
    ("opt_game_center",    "toggle", "advanced"),
)

OPT_SECTIONS = ("opt_sounds", "opt_cards", "opt_interface", "opt_advanced")

# Persistence, and the trap in measuring it. The app writes its settings when it
# goes to the BACKGROUND, not on every change — which is normal, and which makes
# cold_launch() a misleading way to test it. Measured on build 353:
#
#   change -> leave Options -> reopen                       KEPT
#   change -> Home (background) -> kill -> relaunch         KEPT
#   change -> kill straight from the foreground -> relaunch LOST
#
# The third line is NOT a bug: WDA's terminate kills the app from the foreground,
# which no real user can do — the app switcher backgrounds an app before you can
# swipe it away. Read on its own it looks exactly like "the Unity port stopped
# saving settings", so anything checking persistence must press Home first.


def opt_top(swipes: int = 5):
    """Scroll the Options page back to the top.

    Fixed swipes rather than "scroll until the picture stops changing": each
    screenshot costs ~0.8 s on this rig against ~0.4 s for a swipe, so watching
    for the end is several times more expensive than simply over-swiping, and
    over-swiping a page already at its top does nothing.
    """
    for _ in range(swipes):
        scroll(down=False)


def opt_row(label: str, max_swipes: int = 6):
    """Scroll the Options page to <label> and return its row centre y, or None.

    Options is about three screenfuls long, so a row is reached by scrolling
    rather than assumed visible. Searches downward first; a row that has already
    scrolled past is only findable from the top, so a failed pass rewinds and
    tries once more. six swipes clears the whole page, and keeping that bound
    tight matters — every swipe that finds nothing still costs a capture.

    Reading MANY rows this way is wasteful; use opt_scan() for that.
    """
    frame = _screen_image()
    pos = find(label, screen=frame)
    if pos is not None:
        return _opt_clear_edge(label, pos[1])

    # Not on screen. Which way to scroll is worth ONE capture to answer: OPT_ROWS
    # is in page order, so whichever rows are visible say whether the target is
    # above or below. Guessing instead costs a whole sweep in the wrong direction
    # (~11 s) before anything rewinds.
    order = [n for n, _k, _s in OPT_ROWS]
    down = True
    if label in order:
        here = [i for i, n in enumerate(order) if find(n, screen=frame)]
        if here:
            down = order.index(label) > max(here)
    for go_down in (down, None):
        if go_down is None:                 # last resort: rewind and re-search
            opt_top()
            go_down = True
        if scroll_to(label, max_swipes=max_swipes, down=go_down):
            pos = find(label)
            if pos is not None:
                return _opt_clear_edge(label, pos[1])
    return None


def _opt_clear_edge(label: str, cy: int) -> int:
    """Nudge a row away from the screen edge, so its CONTROL is fully visible.

    scroll_to stops the moment the LABEL matches, which can leave the row at the
    very bottom — and everything read afterwards sits beside or below the label:
    opt_knob looks ~0.022 h either side, opt_kind ~0.024 h below. A row at
    y=1750 on an 828x1792 screen has its end-mark row running off the bottom,
    where it reads as "no marks" — i.e. a slider silently reported as a
    toggle. One short scroll costs far less than that class of wrong answer.
    """
    _, h = screen_size()
    lo, hi = 0.10 * h, h - 0.09 * h
    if lo <= cy <= hi:
        return cy
    scroll(down=cy > hi, frac=0.16)
    pos = find(label)
    return cy if pos is None else pos[1]


def opt_scan(rows=None, screens: int = 6) -> dict:
    """Walk Options top to bottom once, reading every row on the way.

    Returns {label: (row centre y, "toggle"|"slider")} for each row seen.

    One capture per SCREENFUL rather than per row. A capture costs ~0.5 s on
    this rig and matching all twelve row labels against it ~0.6 s, so reading the
    page in one pass is several times cheaper than locating each row on its own —
    which would additionally have to rewind to the top every time it asked for a
    row that had already scrolled past.

    Kept deliberately although nothing calls it right now: verifyOptions was
    narrowed to four named rows, and this is the tool for reading MANY of them —
    what a full-page inventory check would want again.
    """
    rows = rows or OPT_ROWS
    want = {label for label, _kind, _sect in rows}
    _, h = screen_size()
    # A row is only read when its whole control fits on screen: opt_knob looks a
    # little either side of the label and opt_kind a little BELOW it, so a row
    # sitting at the very bottom edge would be misread as having no end marks.
    # Skipping it leaves it in `want` for the next screenful to catch.
    lo, hi = 0.06 * h, h - 0.05 * h
    found = {}
    opt_top()
    for _ in range(screens):
        frame = _screen_image()
        for label in sorted(want):
            pos = find(label, screen=frame)
            if pos is None or not (lo <= pos[1] <= hi):
                continue
            kind = opt_kind(pos[1], screen=frame)
            if kind is None:                # band clipped — next screenful
                continue
            found[label] = (pos[1], kind)
            want.discard(label)
        if not want:
            break
        scroll(down=True)
    return found


def opt_knob(cy: int, screen=None):
    """(centre x, width) of the white knob on the row centred at `cy`, or None.

    The knob is the widest run of near-white pixels in the control column at
    that row — true of both a toggle's knob and a slider's. Everything else in
    the column (track, pill, felt) is far from white, so the run is unambiguous.

    `screen` takes a frame already captured by _screen_image(), so a caller
    reading several rows pays for one capture instead of one per row. Near-white
    is channel-order agnostic, so BGR-vs-RGB does not matter here.
    """
    import numpy as np
    w, h = screen_size()
    a = (_screen_image() if screen is None else screen).astype(int)
    y0, y1 = max(0, int(cy - OPT_ROW_BAND * h)), min(h, int(cy + OPT_ROW_BAND * h))
    x0, x1 = int(OPT_TRACK_L * w) - 12, int(OPT_TRACK_R * w) + 12
    sub = a[y0:y1, x0:x1]
    white = (sub[:, :, 0] > 222) & (sub[:, :, 1] > 222) & (sub[:, :, 2] > 222)
    # A column counts as knob only if it is white down most of the band, which
    # rules out the row's white LABEL text bleeding into the window.
    cols = np.where(white.sum(axis=0) >= max(3, (y1 - y0) // 4))[0]
    if len(cols) == 0:
        return None
    runs = []
    for c in cols:
        if runs and c - runs[-1][-1] <= 3:
            runs[-1].append(c)
        else:
            runs.append([c])
    best = max(runs, key=len)
    if len(best) < 0.05 * w:            # too narrow to be a knob
        return None
    return (best[0] + best[-1]) / 2.0 + x0, len(best)


def opt_kind(cy: int, screen=None):
    """"slider" / "toggle" for the row centred at `cy`, or None if unreadable.

    Told apart by the "-"/"+" end marks, which only a slider has. Knob position
    cannot do this job: a slider's knob ranges over the whole track and so can
    sit exactly where a toggle's does. Measured on both Options captures, the
    two cells hold 20-71 white pixels on every slider and exactly 0 on every
    toggle.
    """
    w, h = screen_size()
    a = (_screen_image() if screen is None else screen).astype(int)
    gy = int(cy + OPT_MARKS_DY * h)
    y0, y1 = gy - 14, gy + 14
    if y0 < 0 or y1 > h:
        # The mark row runs off the screen, so "no marks" would be a
        # measurement artefact rather than a fact about the row. Say so.
        return None
    for fx in (OPT_MINUS_X, OPT_PLUS_X):
        cx = int(fx * w)
        cell = a[y0:y1, max(0, cx - 20):cx + 20]
        white = (cell[:, :, 0] > 215) & (cell[:, :, 1] > 215) & (cell[:, :, 2] > 215)
        if white.sum() < 8:
            return "toggle"
    return "slider"


def toggle_state(label: str):
    """True (on) / False (off) / None (row or knob not found)."""
    cy = opt_row(label)
    if cy is None:
        return None
    knob = opt_knob(cy)
    if knob is None:
        return None
    return knob[0] > OPT_PILL_C * screen_size()[0]


def tap_toggle(label: str, settle: float = 1.2):
    """Tap the toggle on <label>'s row. Returns its state afterwards."""
    cy = opt_row(label)
    if cy is None:
        return None
    w, _ = screen_size()
    tap_at((int(OPT_PILL_C * w), int(cy)), settle=settle)
    return toggle_state(label)


def set_toggle(label: str, on: bool, settle: float = 1.2) -> bool:
    """Put the toggle on <label>'s row into `on`. True if it ends up there."""
    now = toggle_state(label)
    if now is None:
        return False
    if now == on:
        return True
    return tap_toggle(label, settle=settle) == on


def slider_value(label: str):
    """The slider on <label>'s row as 0.0 (min) .. 1.0 (max), or None."""
    cy = opt_row(label)
    if cy is None:
        return None
    knob = opt_knob(cy)
    return None if knob is None else _value_from(knob)


def _value_from(knob) -> float:
    """Knob centre -> 0..1. The knob cannot overhang the track, so its own
    half-width is what the usable travel is short of the track at each end."""
    cx, kw = knob
    w = screen_size()[0]
    lo, hi = OPT_TRACK_L * w + kw / 2.0, OPT_TRACK_R * w - kw / 2.0
    return max(0.0, min(1.0, (cx - lo) / (hi - lo)))


# There is deliberately no "press + / press -" helper. On this build those marks
# are LABELS, not buttons: they annotate the low and high end of the track, which
# is also what the row's own caption says ("Move slider to change the volume").
# Measured before concluding it — 36 points swept across a +/-30 x -25..+40 px
# grid over both glyphs, 3 taps each, plus a 2 s press-and-hold, plus taps on the
# track either side of the knob: the value never moved and the whole-screen diff
# was 0.00000, i.e. the app did not so much as flicker. Dragging the knob is the
# only interaction a slider has.


def slider_drag(label: str, value: float, duration: float = 0.5):
    """Drag <label>'s slider knob to `value` (0..1). Returns the value reached.

    The extremes are driven a little PAST the track end so the control clamps
    there — stopping exactly on the end pixel tends to land a step short.
    """
    cy = opt_row(label)
    if cy is None:
        return None
    knob = opt_knob(cy)
    if knob is None:
        return None
    w, _ = screen_size()
    lo, hi = OPT_TRACK_L * w + knob[1] / 2.0, OPT_TRACK_R * w - knob[1] / 2.0
    target = lo + max(0.0, min(1.0, value)) * (hi - lo)
    if value <= 0.02:
        target = OPT_TRACK_L * w - 20
    elif value >= 0.98:
        target = OPT_TRACK_R * w + 20
    swipe((int(knob[0]), int(cy)), (int(target), int(cy)), duration=duration)
    time.sleep(0.8)
    return slider_value(label)


def slider_set(label: str, value: float, tol: float = 0.03, tries: int = 3):
    """Drag <label>'s slider to `value` and keep correcting until it sticks.

    One drag lands within ~0.07 of a mid-track target — the knob follows the
    finger but settles a little short. That is fine for "did it move?", not for
    landing on a value someone asked for, so this re-drags from wherever the knob
    ended up. Each correction starts closer, so it converges.
    """
    got = slider_drag(label, value)
    for _ in range(tries - 1):
        if got is None or abs(got - value) <= tol:
            break
        got = slider_drag(label, value)
    return got


def opt_get(label: str, kind: str):
    """Read <label>'s row without caring which control it carries.

    Returns True/False for a toggle, 0.0..1.0 for a slider, None if the row or
    its knob could not be found. A caller driving a mixed set of rows (see
    tests/verifyOptions.py) would otherwise have to branch on `kind` at every
    single read, and the knowledge of how each kind is read already lives here.
    """
    return toggle_state(label) if kind == "toggle" else slider_value(label)


def opt_put(label: str, kind: str, value):
    """Drive <label>'s row to `value`. Returns what it actually ended at.

    The counterpart to opt_get, and the same argument for living here. Note it
    reports the value REACHED rather than a did-it-work boolean, so a caller can
    say how far off a control that refused to move ended up.
    """
    if kind != "toggle":
        return slider_set(label, value)
    now = toggle_state(label)
    if now is None or now == bool(value):
        return now
    return tap_toggle(label)        # already returns the state afterwards


# ── gameplay ──────────────────────────────────────────────────────
def open_picker(timeout: float = 6.0) -> bool:
    """From the menu, tap Play and land on the difficulty picker."""
    if not tap("menu_play", settle=2.0):
        return False
    return at_screen("difficulty", timeout)


def start_game(level: str = "easy", timeout: float = 12.0) -> bool:
    """From the difficulty picker, deal a game at `level`.

    Handles the confirmation that choosing a level raises when another game is
    already paused, and the first-game rules offer. Returns True once the game
    table is up.
    """
    anchor = f"difficulty_{level}"
    if not tap(anchor, settle=2.5):
        return False
    settle_prompts()
    return at_screen("table", timeout)


def resume_game(timeout: float = 12.0) -> bool:
    """Tap the picker's Resume banner (only shown when a game is paused)."""
    if not (have("resume") and tap("resume", settle=3.0)):
        return False
    settle_prompts()
    return at_screen("table", timeout)


def at_table(timeout: float = 6.0) -> bool:
    return at_screen("table", timeout)


def menu_button_pos():
    """Where the in-game top bar's 'menu' control is, or None.

    Prefers the template, but falls back to MIRRORING 'back' across the screen —
    measured on both an iPhone 11 and an iPhone 16 Pro, the two controls share a
    y and the menu sits within 10px of the mirrored x, against a target ~140px
    wide.

    The fallback earns its keep because 'menu' is white text sitting ON THE FELT,
    so its match score moves with whatever surface Choose Look last applied: it
    measured 0.74-0.84 across surfaces on the same device and the same real
    table. No fixed threshold survives that. 'back' is artwork rather than text
    on felt and holds 0.97 regardless, so it is the sounder anchor.
    """
    pos = find("in_game_menu")
    if pos:
        return pos
    b = find("back_game")
    if b is None:
        return None
    w, _ = screen_size()
    return (w - b[0], b[1])


def open_ingame_menu(timeout: float = 5.0) -> bool:
    """Open the in-game drawer (replay/abandon/options/new/help/faq).

    Idempotent — tapping the top-bar 'menu' while the drawer is already open
    would close it again, so this checks first.
    """
    if seen("ingame_replay", timeout=1.0):
        return True
    pos = menu_button_pos()
    if pos is None:
        return False
    tap_at(pos, settle=1.5)
    return seen("ingame_replay", timeout=timeout)


def close_ingame_menu(timeout: float = 4.0) -> bool:
    if not is_on("ingame_replay"):
        return True
    pos = menu_button_pos()
    if pos is None:
        return False
    tap_at(pos, settle=1.5)
    return not seen("ingame_replay", timeout=timeout)


# ── Dev Panel (the QA cheats) ─────────────────────────────────────
# The Unity build keeps a developer panel behind the same hidden gesture the
# Obj-C build used for its QA cheats: 5 rapid taps on the About screen's spider
# emblem reveal a "Dev Panel" button, and tapping that expands a list —
# surface / language / card-back pickers, "Complete Game", "Max Debugger",
# "Kill Banner Ad", "PT Debugger", "Screen Stats".
#
# "Complete Game" is the synthetic win. It acts on the ACTIVE game, so firing it
# from the About screen does nothing at all (measured: 0.00% of the screen) —
# the panel has to be armed first and the cheat fired from the table.
#
# The expanded panel is a persistent overlay: it follows you across screens,
# which is what makes that possible. The cost is that it covers the right-hand
# column, which is exactly where the main menu draws its labels — so on_menu()
# and to_menu() cannot confirm the menu while it is up. Navigate with controls
# that stay clear of it (About's top-left back, Play, Easy) or close it first.
def unlock_dev_panel(taps: int = 5, timeout: float = 6.0) -> bool:
    """From the About screen, reveal the Dev Panel button. Idempotent.

    Only the GESTURE is tied to About (that is where the emblem is). Once
    unlocked the button itself appears on every screen, and stays until the app
    is relaunched.
    """
    if is_on("dev_panel"):
        return True
    if not is_on("about_emblem"):
        return False
    x, y = find("about_emblem")
    rapid_tap((x, y), times=taps)
    return seen("dev_panel", timeout)


def open_dev_panel(from_menu: bool = True) -> bool:
    """Arm the cheats: unlock on About and expand the panel. Idempotent."""
    if is_on("dev_complete_game"):
        return True
    if from_menu and not tap("menu_about", settle=2.5):
        return False
    if not at_screen("about", 6.0):
        return False
    if not unlock_dev_panel():
        return False
    if not tap("dev_panel", settle=2.0):
        return False
    return seen("dev_complete_game", 4.0)


def close_dev_panel(settle: float = 1.5) -> bool:
    """Collapse the overlay so on_menu()/to_menu() can see the menu again."""
    if not is_on("dev_complete_game"):
        return True
    if not tap("dev_panel", settle=settle):
        return False
    return not seen("dev_complete_game", 1.0)


def complete_game(settle: float = 5.0) -> bool:
    """Fire the QA synthetic win. Needs a game ACTIVE and the panel armed."""
    if not is_on("dev_complete_game"):
        return False
    return tap("dev_complete_game", settle=settle)


def win_current_game(timeout: float = 10.0) -> bool:
    """Win the game ALREADY on the table with the QA cheat. True once on victory.

    Needs the Dev Panel button showing (openDebugTools / unlock_dev_panel) and the
    table up. Leaves the panel EXPANDED over the victory screen — call
    close_dev_panel() before navigating, or to_menu() cannot see the menu labels
    the overlay covers.
    """
    settle_prompts()            # the "Did you know?" tip lands AFTER the deal and
                                # swallows taps until answered
    if not is_on("dev_complete_game"):          # not expanded yet
        if not is_on("dev_panel"):
            return False
        if not tap("dev_panel", settle=2.0):
            return False
    if not complete_game():
        return False
    return at_screen("victory", timeout=timeout)


def win_game(level: str = "easy", arm: bool = True) -> bool:
    """Arm the cheat, deal a game at `level`, and win it. True once on victory.

    Collapses the panel before navigating and re-expands it on the table. That
    ordering is not cosmetic: expanded, the overlay covers the Hard/Bold/Expert
    rows of the difficulty picker (and the menu labels on_menu() checks), so
    driving with it open would only ever reach Easy. Only the unlock GESTURE is
    tied to the About screen — the button itself follows you everywhere, so it
    can be re-expanded once the game is dealt.

    arm=False skips the About trip and the 5-tap gesture, and requires the Dev
    Panel button to be showing already (openDebugTools does the unlock). That is
    only safe because launch_app() no longer restarts the app, so an earlier
    test's unlock survives; a restart hides the button again.
    """
    if arm:
        if not open_dev_panel():
            return False
    elif not is_on("dev_panel"):
        return False
    if not close_dev_panel():
        return False
    if not to_menu():
        return False
    if not open_picker():
        return False
    if not tap(f"difficulty_{level}", settle=2.5):
        return False
    settle_prompts()
    if not at_table(timeout=12.0):
        return False
    return win_current_game()   # settles the tip, re-expands over the table, cheats


# ── game-table controls ───────────────────────────────────────────
# The undo / lower / hints targets are the artwork directly BELOW their captions
# and have no distinctive template of their own, so they're tapped at an offset
# from the caption. Anchoring to the caption (rather than a fixed point) keeps
# this correct when the layout shifts between builds.
TABLE_CAPTIONS = {"undo": "tap_undo", "lower": "tap_lower", "hints": "tap_hints"}

# Caption -> button offset, as a fraction of screen height. Deliberately PER
# CONTROL, not one shared number, because the three are not built the same way:
# "tap to undo" and "tap for hints" are captions sitting ABOVE a widget (the
# last-moved cards, the hint deck) and the widget is the button, but "tap to
# lower" has no widget — the caption and its little arrow ARE the button, and
# what sits below them is the score, timer and multiplier, which are inert.
#
# This was one shared 0.044 and that made "lower" a no-op. Measured on the
# iPhone 11, build 363, by tapping four points down that column and sampling the
# board: the caption itself moves 25.42% of the board, the arrow 40 px below it
# 25.42%, and the +0.044h point every control used to be sent to moves 0.002% —
# it lands on the inert score counter. So the control was never actually being
# driven, and nothing noticed because nothing asserted on it.
_CONTROL_DY = {"undo": 0.044, "lower": 0.0, "hints": 0.044}


def tap_table_control(which: str, settle: float = 1.5) -> bool:
    """Tap the game table's 'undo' / 'lower' / 'hints' control."""
    caption = TABLE_CAPTIONS.get(which)
    if caption is None:
        raise ValueError(f"unknown table control: {which}")
    _, h = screen_size()
    return tap_near(caption, dy=int(_CONTROL_DY[which] * h), settle=settle)


# Top bar -> stock-pile centre, as a fraction of screen height. Measured on the
# iPhone 11 (828x1792): the bar sits at y=160 and the pile at y=297, so 137 px.
_STOCK_BELOW_BAR = 0.0765


def tap_stock(settle: float = 2.5) -> bool:
    """Tap the stock pile to deal a new row across the tableau.

    Prefers the stock_pile template; falls back to the pile's position in the
    table layout when that crop isn't available yet.

    That fallback is anchored to the TOP BAR rather than to the screen, because
    the table has two layouts. "tap to lower" slides the whole playfield down —
    on the iPhone 11 the bar goes y=160 -> 232 and the stock pile 297 -> 369 —
    and it is a persistent SETTING that survives leaving the game. A blind screen
    fraction therefore misses the pile on every run after anyone leaves the table
    lowered, and reports it as "dealing from the stock did not change the board":
    a failure a long way from its cause. Anchoring costs one template match and
    removes the whole class.
    """
    if have("stock_pile") and tap("stock_pile", settle=settle):
        return True
    w, h = screen_size()
    bar = find("back_game")
    y = bar[1] + int(_STOCK_BELOW_BAR * h) if bar else int(h * 0.166)
    tap_at((int(w * 0.652), y), settle=settle)
    return True


def board_box():
    """Crop box over the playing area only.

    Excludes the status bar and top bar (a live clock and a running timer would
    register as change on every capture) and the bottom control strip / ad
    banner, leaving the stock, foundations and tableau — the part that actually
    reflects game state.
    """
    w, h = screen_size()
    return (0, int(h * 0.12), w, int(h * 0.70))


# ── pixel observation ─────────────────────────────────────────────
# Unity publishes no state to read, so "did that control do anything?" has to be
# answered from the screen itself: capture before, act, capture after, compare.
# A dead control produces an identical image; a live one cannot.
def region(path, box=None):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    return im.crop(box) if box else im


def diff_frac(a, b) -> float:
    """Fraction of pixels that differ meaningfully between two PIL images."""
    import numpy as np
    ia = np.asarray(a, dtype=np.int16)
    ib = np.asarray(b, dtype=np.int16)
    if ia.shape != ib.shape:
        return 1.0
    return float((np.abs(ia - ib).max(axis=2) > 12).mean())


def changed(a, b, min_frac: float = 0.005) -> bool:
    return diff_frac(a, b) > min_frac


def board_shot(tag: str):
    """Capture just the playing area, for before/after comparisons."""
    return region(shoot(f"_board_{tag}"), board_box())


def board_frame():
    """The playing area as a BGR frame, to hand to find(screen=...).

    The sibling of board_shot(): that one returns a PIL crop for pixel
    comparison, this one returns the same crop in the form find() matches
    against — for when a template must not be allowed to answer from chrome
    OUTSIDE the board. The suit check in tests/verifyGamePlay.py needs exactly
    that: the bottom "tap to undo" widget draws a red heart whatever suit the
    deal is using, because it is decorative art rather than part of the game.
    """
    x0, y0, x1, y1 = board_box()
    return _screen_image()[y0:y1, x0:x1]


def peak_change_after(action, frames: int = 6, interval: float = 0.3,
                      tag: str = "peak") -> float:
    """Run `action`, then sample the board and return the LARGEST change seen.

    Some Unity feedback is transient. The hint highlight, for instance, plays
    for well under a second and the board then returns to *exactly* its previous
    pixels — so a single capture taken after the usual settle sees no difference
    and would wrongly read as "the control did nothing". Sampling across the
    window catches the peak instead of racing the animation.
    """
    before = board_shot(f"{tag}_0")
    action()
    peak = 0.0
    for i in range(frames):
        time.sleep(interval)
        peak = max(peak, diff_frac(before, board_shot(f"{tag}_{i + 1}")))
    return peak
