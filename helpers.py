"""Small WDA helpers shared by the test scripts.

Airtest's `start_app()` doesn't reliably foreground iOS apps, so we launch via
the WebDriverAgent session API (creating a session with a bundleId launches and
foregrounds that app). Use these alongside Airtest, which then drives whatever
is on screen (snapshot / touch / image matching).
"""
import json
import subprocess
import sys
import urllib.request

import config


# Most recent WDA session id (set by launch_app) so alert helpers can be called
# without threading the id through every caller.
_CURRENT_SESSION = None


def session_alive(session_id: str = None, base_url: str = None,
                  timeout: int = 8) -> bool:
    """True when this WDA session still answers. Does not relaunch XCTest."""
    sid = session_id or _CURRENT_SESSION
    if not sid:
        return False
    try:
        urllib.request.urlopen(
            (base_url or config.WDA_URL) + f"/session/{sid}/window/size",
            timeout=timeout)
        return True
    except Exception:  # noqa: BLE001
        return False


def open_session(bundle_id: str = None, base_url: str = None, timeout: int = 30,
                 force: bool = False) -> str:
    """Create a WDA session against the already-running agent.

    Never launches XCTest — ``scripts/wda.sh`` owns that. Airtest's recover
    path tries ``SolitaireUITests.xctrunner`` and raises "Failed to re-acquire
    session"; callers should call this instead.

    ``bundle_id`` set: attach/launch that app (same as ``launch_app``).
    ``bundle_id`` None: session on whatever is already front, so an App Store
    or Mail hand-off can keep tapping without yanking Spider forward.
    """
    global _CURRENT_SESSION
    base_url = base_url or config.WDA_URL
    if not bundle_id:
        sid = None
        try:
            sid = wda_status(base_url, timeout=8).get("sessionId")
        except Exception:  # noqa: BLE001
            sid = _CURRENT_SESSION
        if sid and session_alive(sid, base_url):
            _CURRENT_SESSION = sid
            return sid
    always = {}
    if bundle_id:
        always["bundleId"] = bundle_id
        always["forceAppLaunch"] = bool(force)
        always["shouldTerminateApp"] = False
    body = json.dumps({"capabilities": {"alwaysMatch": always}}).encode()
    req = urllib.request.Request(
        base_url + "/session", data=body, headers={"Content-Type": "application/json"}
    )
    sid = json.load(urllib.request.urlopen(req, timeout=timeout))["value"]["sessionId"]
    _CURRENT_SESSION = sid
    try:
        _wda_post(f"/session/{sid}/wda/settings",
                  {"settings": {"defaultAlertAction": "accept"}}, base_url)
    except Exception:  # noqa: BLE001
        pass
    return sid


def launch_app(bundle_id: str = None, base_url: str = None, timeout: int = 30,
               force: bool = False) -> str:
    """Foreground an app via WDA and return the session id.

    By default this ATTACHES to the app if it is already running instead of
    restarting it (forceAppLaunch=False). WDA's own default is to relaunch on
    every new session, which silently threw away in-app state between tests —
    most visibly the Dev Panel button, which the hidden QA gesture reveals and a
    relaunch hides again, so no test could build on another's unlock.

    If the app is not running it is launched, so callers still get a foregrounded
    app either way. Pass force=True for a deliberate fresh start (cold_launch).
    """
    return open_session(bundle_id=bundle_id or config.BUNDLE_ID,
                        base_url=base_url, timeout=timeout, force=force)


def current_session() -> str:
    """The session id from the most recent launch_app (or None)."""
    return _CURRENT_SESSION


def wda_status(base_url: str = None, timeout: int = 15) -> dict:
    """Return WDA /status (raises if WDA is not reachable)."""
    base_url = base_url or config.WDA_URL
    return json.load(urllib.request.urlopen(base_url + "/status", timeout=timeout))["value"]


# ── device / app identity ──────────────────────────────────────────
# For assertions about text the app writes ABOUT its environment — the feedback
# mail's subject names the build and the hardware it came from.
#
# Read LIVE, never written into a test as constants. That subject is different
# on every device by design, so a test carrying "26.5" is a test that works on
# one phone until the next iOS update. Reading them here is what lets
# tests/submitFeedback.py run unchanged on the iPhone 14 Pro Max and 16 Pro.
#
# WDA cannot supply the model: /wda/device/info answers "iPhone" for every
# iPhone, too generic to assert anything with. `ideviceinfo` gives the
# identifier the app actually prints (iPhone12,1), and libimobiledevice is
# already a documented dependency of this repo.
#
# All three fail SOFT, returning "", because a missing tool must read as "this
# could not be checked" at the call site rather than crashing a test whose
# subject is something else entirely.

def os_version(base_url: str = None) -> str:
    """The device's iOS version, e.g. "26.5". "" if unreadable."""
    try:
        return str(wda_status(base_url)["os"]["version"])
    except Exception:  # noqa: BLE001
        return ""


def device_model(udid: str = None) -> str:
    """The device's model IDENTIFIER, e.g. "iPhone12,1". "" if unreadable.

    Note this is not the marketing name: iPhone12,1 is sold as "iPhone 11".
    The app prints the identifier, so that is what tests compare against.
    """
    cmd = ["ideviceinfo", "-k", "ProductType"]
    udid = udid or config.DEVICE_UDID
    if udid:
        cmd[1:1] = ["-u", udid]
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def app_info(bundle_id: str = None, udid: str = None):
    """(display name, version) for an installed app, or ("", "") if unreadable.

    e.g. ("Spider", "8.0.0"). The DISPLAY NAME matters as much as the version:
    the feedback subject says "Spider", while config.GAME_NAME is "Spider
    Solitaire" — a test asserting GAME_NAME would fail on a correct app.
    """
    bundle_id = bundle_id or config.BUNDLE_ID
    cmd = [sys.executable, "-m", "tidevice"]
    udid = udid or config.DEVICE_UDID
    if udid:
        cmd += ["--udid", udid]
    cmd += ["applist"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        for line in out.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] == bundle_id:
                return " ".join(parts[1:-1]), parts[-1]
    except Exception:  # noqa: BLE001
        pass
    return "", ""


# ── iOS native alerts (Terms & Conditions, notifications, …) ────────
# WDA drives native alerts through /session/<id>/alert/*. All fail soft (return
# ""/[]/False) so callers can poll safely.
#
# Two limits, both measured on this rig (WDA 15.0.0, iOS 26.5) — they decide
# which mechanism a given prompt needs:
#
#   * /alert/buttons is NOT implemented (404), so alert_buttons() cannot
#     enumerate labels here and falls back to alert_text() + a nameless accept.
#     Anything that only checked alert_buttons() would conclude "no alert" and
#     silently clear nothing.
#   * Alerts presented OUT OF PROCESS are invisible to the session. The App
#     Tracking Transparency prompt is one: /alert/text 404s while it is plainly
#     on screen, whereas the app's own alerts read back fine. ATT therefore has
#     to be matched and tapped as an image (unity_ui: att_prompt / att_deny).

def _wda_post(path: str, body: dict = None, base_url: str = None, timeout: int = 15):
    base_url = base_url or config.WDA_URL
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        base_url + path, data=data, headers={"Content-Type": "application/json"}
    )
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def alert_text(session_id: str, base_url: str = None, timeout: int = 10) -> str:
    """Message of the alert that is up, or "" if none is (or it is invisible).

    This is the reliable presence check on this WDA build — /alert/buttons 404s,
    so an empty button list says nothing about whether an alert is showing.
    """
    base_url = base_url or config.WDA_URL
    try:
        resp = json.load(urllib.request.urlopen(
            base_url + f"/session/{session_id}/alert/text", timeout=timeout))
        return resp.get("value") or ""
    except Exception:  # noqa: BLE001  (no alert -> WDA 404s; treat as none)
        return ""


def alert_buttons(session_id: str, base_url: str = None, timeout: int = 10) -> list:
    """Button labels of the current alert, or [] if none is up OR they can't be read.

    [] is ambiguous on this rig: WDA 15.0.0 has no /alert/buttons endpoint, so it
    also means "an alert may be up, unlabelled". Pair with alert_text() before
    concluding the screen is clear.
    """
    base_url = base_url or config.WDA_URL
    try:
        resp = json.load(urllib.request.urlopen(
            base_url + f"/session/{session_id}/alert/buttons", timeout=timeout))
        return resp.get("value") or []
    except Exception:  # noqa: BLE001  (no alert, or endpoint missing)
        return []


def alert_tap(session_id: str, label: str = None, base_url: str = None) -> bool:
    """Accept the current alert — the named button, or its default if label is None."""
    try:
        _wda_post(f"/session/{session_id}/alert/accept",
                  {"name": label} if label else {}, base_url)
        return True
    except Exception:  # noqa: BLE001
        return False


# ── device radios (Airplane Mode / Wi-Fi) ──────────────────────────
# The suite wants the phone OFFLINE (adverts otherwise interrupt screen
# transitions), while tests/verifyAds.py, tests/visitLastScore.py and
# tests/verifyHelpShiftOnline.py want it online. That used to be a manual step on the
# phone; these drive it.
#
# It works because iOS **Settings is an ordinary app**, so WDA reads its real
# accessibility tree — unlike the game, which is one opaque Unity view with
# nothing published at all. Airplane Mode is a genuine switch in that tree:
#
#   XCUIElementTypeSwitch name="com.apple.settings.airplaneMode" value="1"
#
# so its state can be READ rather than assumed, and only tapped when it is
# actually wrong.
#
# Two things measured on this rig (iPhone 11, iOS 26.5, WDA 15.0.0) that the
# obvious implementation gets wrong:
#
#   * **/element/<id>/click does nothing to this switch.** It returns success and
#     the value stays exactly as it was. The element's rect covers the whole
#     table row, and pressing the row is not pressing the control. A coordinate
#     tap on the toggle itself does work, so that is what this does — derived
#     from the element's own rect, not hardcoded, so it holds on other iPhones.
#   * **Toggling radios does not break the connection.** WDA is reached over the
#     USB cable via iproxy, not over Wi-Fi, so the session survives going
#     offline. This would not be safe on a WiFi-paired device (the iPhone 7).
#
# The ONE hazard, and it is the same one CLAUDE.md records: WDA must be STARTED
# while the phone is online, because iOS re-verifies the developer certificate
# over the network at launch. These helpers are safe because they never restart
# WDA — but a run that goes offline and then tries to relaunch WDA will fail.
SETTINGS_BUNDLE = "com.apple.Preferences"
AIRPLANE_SWITCH = "com.apple.settings.airplaneMode"
WIFI_ROW = "com.apple.settings.wifi"
WIFI_SWITCH = "Wi‑Fi"  # U+2011 non-breaking hyphen, as Settings publishes it

# How far in from the row's RIGHT edge the switch control sits, in points.
# Measured: the Airplane Mode row spans x 20..394 and the toggle answers at
# x=355, i.e. 39 points short of the trailing edge. Points are device
# independent, so this does not need scaling per phone.
_SWITCH_INSET = 39


def _wda_get(path: str, base_url: str = None, timeout: int = 15):
    base_url = base_url or config.WDA_URL
    return json.load(urllib.request.urlopen(base_url + path, timeout=timeout))


def _element(sid: str, name: str, base_url: str = None, timeout: float = 0.0):
    """Element id of the accessibility element called `name`, or None.

    `timeout` polls rather than asking once. Settings does not draw instantly
    after being foregrounded, and a single-shot lookup taken in that window
    reports the row as absent — which read as "the switch is unreadable"
    immediately after every toggle.
    """
    import time
    deadline = time.time() + timeout
    while True:
        try:
            r = _wda_post(f"/session/{sid}/element",
                          {"using": "name", "value": name}, base_url)
            el = (r.get("value") or {}).get("ELEMENT")
            if el:
                return el
        except Exception:                   # noqa: BLE001 — not on screen (yet)
            pass
        if time.time() >= deadline:
            return None
        time.sleep(0.4)


def _typed_element(sid: str, name: str, kind: str, base_url: str = None,
                   timeout: float = 0.0):
    """Element id matching both name and accessibility type."""
    import time
    deadline = time.time() + timeout
    escaped = name.replace("'", "\\'")
    while True:
        try:
            r = _wda_post(
                f"/session/{sid}/element",
                {"using": "predicate string",
                 "value": f"name == '{escaped}' AND type == '{kind}'"},
                base_url)
            el = (r.get("value") or {}).get("ELEMENT")
            if el:
                return el
        except Exception:                   # noqa: BLE001
            pass
        if time.time() >= deadline:
            return None
        time.sleep(0.4)


def _attr(sid: str, el: str, attr: str, base_url: str = None):
    try:
        return _wda_get(f"/session/{sid}/element/{el}/attribute/{attr}",
                        base_url).get("value")
    except Exception:                       # noqa: BLE001
        return None


def _open_settings(base_url: str = None) -> str:
    """Foreground Settings at its ROOT page and return the session id.

    Settings resumes wherever it was last left, which can be a sub-page with no
    Airplane Mode row on it. So this launches, looks for the switch, and only if
    it is missing pays for a terminate + relaunch to force the root page.
    """
    sid = launch_app(SETTINGS_BUNDLE, base_url, timeout=60)
    if _element(sid, AIRPLANE_SWITCH, base_url, timeout=6.0) is None:
        try:
            _wda_post(f"/session/{sid}/wda/apps/terminate",
                      {"bundleId": SETTINGS_BUNDLE}, base_url)
        except Exception:                   # noqa: BLE001
            pass
        sid = launch_app(SETTINGS_BUNDLE, base_url, timeout=60, force=True)
        _element(sid, AIRPLANE_SWITCH, base_url, timeout=_ROW_TIMEOUT)
    return sid


# How long to keep looking for a row before calling it absent. Generous on
# purpose: the Settings ROOT PAGE REBUILDS when the phone comes online — the
# Apple Account row and any "finish setting up your iPhone" follow-up rows load
# in and reflow the list — and a lookup landing inside that rebuild finds
# nothing. That is an intermittent, and it bit exactly one sequence: going
# online and then straight back offline. The first fix re-opened Settings on
# every miss, which created a fresh WDA session each time and eventually timed
# WDA out; waiting is both cheaper and what the situation actually calls for.
_ROW_TIMEOUT = 15.0


def _read_airplane(sid: str, base_url: str = None):
    """True/False/None — the switch's state, using an already-open Settings."""
    el = _element(sid, AIRPLANE_SWITCH, base_url, timeout=_ROW_TIMEOUT)
    if el is None:
        return None
    value = _attr(sid, el, "value", base_url)
    return None if value is None else str(value) in ("1", "true", "True")


def _read_wifi(sid: str, base_url: str = None, timeout: float = _ROW_TIMEOUT) -> str:
    """The Wi-Fi row's state — "Off", "Not Connected", or a network name."""
    el = _element(sid, WIFI_ROW, base_url, timeout=timeout)
    label = _attr(sid, el, "label", base_url) if el else None
    if not label:
        return ""
    # The row's label reads "Wi-Fi, <state>".
    return label.split(",", 1)[1].strip() if "," in label else label.strip()


def _set_wifi(sid: str, want: bool, base_url: str = None) -> bool:
    """Set Wi-Fi from Settings root, leaving Settings on the Wi-Fi page."""
    import time
    row = _element(sid, WIFI_ROW, base_url, timeout=_ROW_TIMEOUT)
    label = _attr(sid, row, "label", base_url) if row else ""
    state = label.split(",", 1)[1].strip() if label and "," in label else label
    if bool(state and state.lower() != "off") == want:
        return True
    rect = _attr(sid, row, "rect", base_url) if row else None
    if not rect:
        return False
    try:
        _wda_post(
            f"/session/{sid}/wda/tap",
            {"x": int(rect["x"] + rect["width"] / 2),
             "y": int(rect["y"] + rect["height"] / 2)},
            base_url)
    except Exception:                       # noqa: BLE001
        return False
    switch = _typed_element(
        sid, WIFI_SWITCH, "XCUIElementTypeSwitch", base_url,
        timeout=_ROW_TIMEOUT)
    rect = _attr(sid, switch, "rect", base_url) if switch else None
    if not rect:
        return False
    current = str(_attr(sid, switch, "value", base_url)) in ("1", "true", "True")
    if current != want:
        try:
            _wda_post(
                f"/session/{sid}/wda/tap",
                {"x": int(rect["x"] + rect["width"] / 2),
                 "y": int(rect["y"] + rect["height"] / 2)},
                base_url)
        except Exception:                   # noqa: BLE001
            return False
        time.sleep(2.0)
    return (
        str(_attr(sid, switch, "value", base_url)) in ("1", "true", "True")
    ) == want


def _tap_airplane(sid: str, want: bool, base_url: str = None,
                  settle: float = 4.0, timeout: float = 45.0) -> bool:
    """Drive the switch to `want` using an already-open Settings. True if it got there."""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        el = _element(sid, AIRPLANE_SWITCH, base_url, timeout=_ROW_TIMEOUT)
        if el is None:
            continue
        if (str(_attr(sid, el, "value", base_url)) in ("1", "true", "True")) == want:
            return True
        rect = _attr(sid, el, "rect", base_url) or {}
        if not rect:
            time.sleep(0.8)
            continue
        x = int(rect["x"] + rect["width"] - _SWITCH_INSET)
        y = int(rect["y"] + rect["height"] / 2)
        try:
            _wda_post(f"/session/{sid}/wda/tap", {"x": x, "y": y}, base_url)
        except Exception:                   # noqa: BLE001
            time.sleep(0.8)
            continue
        time.sleep(settle)
    return _read_airplane(sid, base_url) == want


def network_state(base_url: str = None) -> dict:
    """{"airplane": True/False/None, "wifi": "Off"|"Not Connected"|<network>}.

    One Settings visit for both, because a visit is not cheap — see set_network.
    """
    sid = _open_settings(base_url)
    try:
        return {"airplane": _read_airplane(sid, base_url),
                "wifi": _read_wifi(sid, base_url)}
    finally:
        launch_app(base_url=base_url, timeout=60)


def set_network(online: bool, base_url: str = None, wait: float = 75.0,
                restore: bool = True):
    """Take the device online (True) or offline (False). -> (ok, network name).

    `ok` means both radios ended in the required state: online is Airplane Mode
    off + Wi-Fi on, and offline is Airplane Mode on + Wi-Fi off. The name is
    the Wi-Fi network joined online, or "" when going offline.

    ONE Settings visit does the whole job — toggle, verify, and the wait for
    Wi-Fi to come back — and the game is foregrounded once at the end. That
    matters more than it looks: an earlier version built this out of separate
    public calls that each opened Settings and each handed the screen back, so a
    single online/offline cycle cost about ten app switches. WDA slowed under
    that until lookups were timing out and the toggle reported failure while the
    setting itself was fine. Chattiness was the bug, not the logic.

    `restore` foregrounds the game afterwards WITHOUT restarting it, so in-app
    state survives a mid-suite network change.
    """
    import time
    sid = _open_settings(base_url)
    time.sleep(1.5)                         # let the view finish arriving before
                                            # any tap: WDA can see the switch
                                            # while it is still sliding in, and a
                                            # tap aimed at that rect hits nothing
    try:
        airplane_ok = _tap_airplane(sid, not online, base_url)
        wifi_ok = airplane_ok and _set_wifi(sid, online, base_url)
        ok = airplane_ok and wifi_ok
        net = ""
        if ok and online:
            # _set_wifi() had to enter the Wi-Fi page when it changed the
            # switch. Reopen Settings at root so _read_wifi() can watch its row
            # move from Not Connected to the joined network name.
            if _element(sid, WIFI_ROW, base_url) is None:
                sid = _open_settings(base_url)
            deadline = time.time() + wait
            while time.time() < deadline:
                net = _read_wifi(sid, base_url, timeout=6.0)
                if net and net.lower() not in ("off", "not connected"):
                    break
                time.sleep(2.0)
            if net.lower() in ("off", "not connected"):
                net = ""
        return ok, net
    finally:
        if restore:
            launch_app(base_url=base_url, timeout=60)


def airplane_mode(base_url: str = None):
    """True if the device is in Airplane Mode, False if not, None if unreadable."""
    return network_state(base_url)["airplane"]


def wifi_status(base_url: str = None) -> str:
    """What the Wi-Fi row reports — "Off", "Not Connected", or a network name."""
    return network_state(base_url)["wifi"]

# ── "tap the positive option" heuristic ────────────────────────────
# Affirmative labels (priority order) and declining labels (exact, so short
# words like "No"/"OK" don't match inside other words). Case-insensitive.
_POSITIVE = (
    "allow all", "allow once", "allow while using app", "while using app",
    "always allow", "allow", "ok", "okay", "yes", "continue", "accept",
    "i accept", "agree", "i agree", "got it", "confirm", "sure", "enable",
    "turn on", "rate", "update", "get",
)
_NEGATIVE = {
    "don't allow", "dont allow", "do not allow", "no thanks", "no, thanks",
    "no thank you", "not now", "ask app not to track", "deny", "cancel", "no",
    "later", "maybe later", "skip", "dismiss", "close", "quit", "off",
}


def positive_button(buttons):
    """Pick the affirmative button from an alert's button labels.

    Drops clearly-negative buttons (Don't Allow / Cancel / No / Ask App Not to
    Track / …), then prefers a known-positive label (Allow / OK / Yes / …) by
    priority, else falls back to the last remaining button (iOS convention: the
    trailing/bottom button is usually the affirmative). Returns None if empty.
    """
    if not buttons:
        return None
    pool = [b for b in buttons if b.strip().lower() not in _NEGATIVE] or list(buttons)
    for pos in _POSITIVE:                       # exact match, by priority
        for b in pool:
            if b.strip().lower() == pos:
                return b
    for pos in _POSITIVE:                       # substring match, by priority
        for b in pool:
            if pos in b.strip().lower():
                return b
    return pool[-1]
