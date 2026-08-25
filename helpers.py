"""Small WDA helpers shared by the test scripts.

Airtest's `start_app()` doesn't reliably foreground iOS apps, so we launch via
the WebDriverAgent session API (creating a session with a bundleId launches and
foregrounds that app). Use these alongside Airtest, which then drives whatever
is on screen (snapshot / touch / image matching).
"""
import json
import urllib.request

import config


# Most recent WDA session id (set by launch_app) so alert helpers can be called
# without threading the id through every caller.
_CURRENT_SESSION = None


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
    global _CURRENT_SESSION
    bundle_id = bundle_id or config.BUNDLE_ID
    base_url = base_url or config.WDA_URL
    body = json.dumps({"capabilities": {"alwaysMatch": {
        "bundleId": bundle_id,
        "forceAppLaunch": bool(force),
        "shouldTerminateApp": False,
    }}}).encode()
    req = urllib.request.Request(
        base_url + "/session", data=body, headers={"Content-Type": "application/json"}
    )
    sid = json.load(urllib.request.urlopen(req, timeout=timeout))["value"]["sessionId"]
    _CURRENT_SESSION = sid
    # Best-effort: ask WDA to auto-accept (tap the affirmative button of) any
    # system alert it can see during the session. Harmless if unsupported; the
    # explicit sweep in flows.dismiss_popups() covers what this misses (ATT).
    try:
        _wda_post(f"/session/{sid}/wda/settings",
                  {"settings": {"defaultAlertAction": "accept"}}, base_url)
    except Exception:  # noqa: BLE001
        pass
    return sid


def current_session() -> str:
    """The session id from the most recent launch_app (or None)."""
    return _CURRENT_SESSION


def wda_status(base_url: str = None, timeout: int = 15) -> dict:
    """Return WDA /status (raises if WDA is not reachable)."""
    base_url = base_url or config.WDA_URL
    return json.load(urllib.request.urlopen(base_url + "/status", timeout=timeout))["value"]


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
