"""MAX Mediation Debugger: put MAX in Test Mode on one test network.

Shared by tests/verifyAds.py and tests/triggerAdPoints.py. The debugger is
native UIKit over the Unity view, so everything here is READ from the
accessibility tree with predicate queries (the table is too big to enumerate).

Test Mode: the Ads section's "Test Mode Enabled" row reads true/false. While
it is off, the "Select Test Mode Network" row carries a blue "Enable" link;
tapping it raises MAX's "Restart Required" alert. After OK, Spider is
relaunched from the FOREGROUND (so it lands on the menu, not a restored table
whose Back fires an interstitial), the Dev Panel — re-locked by the relaunch —
is unlocked again, and Test Mode must read true. It lasts ONE app session,
so once ensure_network() has run, every later relaunch (a recovery, a forced
launch) turns it back on before the run continues: ads are only ever
triggered from a test network, never a live one.

Network names are ambiguous: the debugger page lists every network again under
"Completed SDK Integrations", so the network window is confirmed by its
navigation bar before the name is looked for.
"""
import helpers
import unity_ui as ui

CAPTURE = True
# The network every later relaunch must restore, once ensure_network() ran.
_KEPT = None
_BUSY = False


def _shoot(name: str):
    return ui.shoot(name) if CAPTURE else "(capture off)"


# The Ads section's "Select Test Mode Network" row carries a blue "Enable"
# link while Test Mode is off; the "Test Mode Enabled" row below it reads
# true/false.
TEST_NETWORK_ROW = "Select Test Mode Network"
TEST_NETWORK_SELECTED = "Test Mode Network"
TEST_NETWORK_LABELS = (TEST_NETWORK_ROW, TEST_NETWORK_SELECTED)
ENABLE_LINK = "Enable"
TEST_MODE_ENABLED = "Test Mode Enabled"
RESTART_TEXT = "restart required"
NETWORK = "Pangle"   # the default test network
# Sub-windows an interrupted run can leave open over the debugger.
SUBWINDOWS = TEST_NETWORK_LABELS
SWIPES = 8


def _visible_any(labels):
    """``(label, rect)`` of the first label drawn on screen, else ``(None, None)``."""
    for label in labels:
        rect = ui._ax_rect(label, kind=None)
        if rect:
            return label, rect
    return None, None


def _tap_rect(rect, settle: float = 2.5) -> bool:
    ok = ui._tap_point(rect["x"] + rect["width"] / 2,
                       rect["y"] + rect["height"] / 2)
    if ok:
        ui.sleep(settle)
    return ok


def _reopen_debugger():
    ui.expect(ui.close_max_debugger(),
              "could not close the debugger to reset its scroll")
    ui.expect(ui.tap_max_debugger(),
              "could not reopen Max Debugger from Debug after a failed scroll")
    ui.expect(ui.on_max_debugger(),
              "reopening Max Debugger did not bring it back")


def _scroll_to_any(labels):
    """Scroll the debugger until one of ``labels`` is VISIBLE.

    The search only goes DOWN, so a leftover scroll position can put the row
    ABOVE the viewport; one close-and-reopen from the top covers that.
    """
    for attempt in range(2):
        for _ in range(SWIPES):
            label, rect = _visible_any(labels)
            if label:
                return label, rect
            ui.scroll(down=True)
        label, rect = _visible_any(labels)
        if label or attempt:
            return label, rect
        print(f"  {labels[0]!r} not in view — reopening the debugger from "
              f"the top")
        _reopen_debugger()
    return None, None


def _visible_rects(name: str) -> list:
    """Rects of every VISIBLE native element called ``name``."""
    sid = helpers.current_session()
    escaped = name.replace("'", "\\'")
    try:
        found = helpers._wda_post(
            f"/session/{sid}/elements",
            {"using": "predicate string",
             "value": f"name == '{escaped}' AND visible == 1"},
            timeout=30).get("value")
    except Exception:  # noqa: BLE001
        return []
    rects = []
    for el in found or []:
        eid = el.get("ELEMENT") or (list(el.values())[0] if el else None)
        rect = helpers._attr(sid, eid, "rect") if eid else None
        if rect:
            rects.append(rect)
    return rects


def _same_line(a, b) -> bool:
    return abs((a["y"] + a["height"] / 2) - (b["y"] + b["height"] / 2)) <= max(
        a["height"], b["height"], 24)


def _on_line_of(row_rect, name: str):
    """Rect of the visible ``name`` drawn on the same line as ``row_rect``."""
    for rect in _visible_rects(name):
        if _same_line(row_rect, rect):
            return rect
    return None


def _test_mode_state():
    """``(on, evidence)`` from the debugger's "Test Mode Enabled" row.

    The row is scrolled into view first: values are matched to it by line, and
    off-screen rows report rects that cannot be trusted. ``on`` is None when
    the row is missing or reads neither true nor false.
    """
    label, rect = _scroll_to_any((TEST_MODE_ENABLED,))
    if not label:
        return None, f"no {TEST_MODE_ENABLED!r} row in the debugger"
    for value, on in (("true", True), ("false", False)):
        if _on_line_of(rect, value):
            return on, f"{TEST_MODE_ENABLED!r} reads {value}"
    return None, f"{TEST_MODE_ENABLED!r} reads neither true nor false"


def _row_shows(network: str, row_rect) -> bool:
    """True when ``network`` is drawn on the same line as the row."""
    return bool(row_rect and _on_line_of(row_rect, network))


def _wait_alert(timeout: float = 10.0) -> str:
    deadline = ui.time.time() + timeout
    while True:
        text = ui.alert_now()
        if text or ui.time.time() >= deadline:
            return text
        ui.sleep(1)


def _ok_alert(what: str) -> bool:
    """Press OK on the alert that is up — by alert API, then by button name."""
    if helpers.alert_tap(helpers.current_session(), "OK"):
        ui.sleep(2)
        if not ui.alert_now():
            return True
    if ui._tap_named("XCUIElementTypeButton", "OK"):
        ui.sleep(2)
        return True
    print(f"  could not press OK on {what}")
    return False


def _open_debugger():
    """Dev Panel (unlocking it if needed) -> Debug -> Max Debugger."""
    ui.expect(ui.open_dev_panel(),
              "could not open the Dev Panel. It is revealed by 5 RAPID TAPS on "
              "the About screen's spider emblem (the emblem, not the wordmark "
              "below it — the wordmark is inert), and the gesture TOGGLES, so a "
              "second burst hides it again.")
    ui.expect(ui.is_on("dev_debug") or ui.is_on("dev_max_debugger"),
              "the Dev Panel opened but has no 'Debug' row — the panel's "
              "contents may have changed in this build")
    panel = _shoot("ad_dev_panel")
    print(f"  Dev Panel is open — Max Debugger is under Debug — see {panel}")
    ui.expect(ui.tap_max_debugger(),
              "the 'Max Debugger' row could not be opened from Debug")
    ui.expect(ui.on_max_debugger(),
              f"tapping 'Max Debugger' did not open MAX's mediation debugger "
              f"— {ui.MAX_DEBUGGER!r} is not in the accessibility tree. The "
              f"foreground app is {ui.active_app() or 'unknown'}.")
    shot = _shoot("ad_max_debugger")
    print(f"  MAX Mediation Debugger is open — see {shot}")


def _relaunch_to_menu(why: str):
    """Kill Spider from the foreground and relaunch it onto the main menu.

    No Home first, on purpose: backgrounded, Spider saves the game and the
    relaunch restores the TABLE, and reaching About from there means Back,
    which fires an interstitial online. MAX keeps its own flag either way.
    """
    print(f"  relaunching Spider ({why})")
    if ui.cold_launch():
        return
    if ui.in_app() and ui.lost(timeout=2.0):
        print("  an ad covered the relaunch — clearing it")
        ui.expect(ui.ad_free(), "an ad after the relaunch would not close")
    ui.expect(ui.on_menu(timeout=8.0) or ui.launch_to_menu(),
              f"Spider did not come back to the main menu after the "
              f"relaunch ({why})")


LIVE_NETWORK_LABELS = ("Select Live Network", "Live Network")


def _tap_enable_and_relaunch(row_labels, want_on: bool):
    """Tap the "Enable" link on a mode row, OK "Restart Required", relaunch.

    The link sits on the TEST row while Test Mode is off and on the LIVE row
    while it is on, so the same step switches either way. Afterwards the
    debugger is reopened and must read ``want_on``.
    """
    label, row = _scroll_to_any(row_labels)
    ui.expect(label,
              f"never brought {row_labels[0]!r} into view in {SWIPES} "
              f"swipes (and a reopen-from-the-top did not help)")
    link = _on_line_of(row, ENABLE_LINK)
    ui.expect(link, f"the {label!r} row shows no {ENABLE_LINK!r} link")
    ui.expect(_tap_rect(link), f"the {ENABLE_LINK!r} link could not be tapped")

    text = _wait_alert()
    shot = _shoot("ad_restart_required")
    if text:
        print(f"  pop-up after {ENABLE_LINK!r}: {text!r} — see {shot}")
        ui.expect(RESTART_TEXT in text.lower(),
                  f"tapping {ENABLE_LINK!r} raised a pop-up that does not "
                  f"say {RESTART_TEXT!r}: {text!r} (see {shot})")
    else:
        ui.expect(ui._ax_first("XCUIElementTypeButton", "OK", timeout=6.0),
                  f"tapping {ENABLE_LINK!r} raised no {RESTART_TEXT!r} "
                  f"pop-up (see {shot})")
        print(f"  pop-up text is not readable over WDA; pressing its OK — "
              f"see {shot}")
    ui.expect(_ok_alert(f"the {RESTART_TEXT!r} pop-up"),
              f"could not press OK on the {RESTART_TEXT!r} pop-up")

    mode = "on" if want_on else "off"
    _relaunch_to_menu(f"switching MAX Test Mode {mode} needs a restart")
    _open_debugger()
    on, evidence = _test_mode_state()
    ui.expect(on is want_on,
              f"MAX Test Mode is not {mode} after the relaunch — {evidence}")
    print(f"  Test Mode is {mode} after the relaunch — {evidence}")


def _enable_test_mode_and_relaunch():
    _tap_enable_and_relaunch((TEST_NETWORK_ROW,), want_on=True)


def _disable_test_mode_and_relaunch():
    _tap_enable_and_relaunch(LIVE_NETWORK_LABELS, want_on=False)


def _open_test_network_window(row_label: str, row_rect,
                               network: str = NETWORK) -> str:
    """Tap the test-network row and confirm the window it opens."""
    ui.expect(_tap_rect(row_rect), f"{row_label!r} could not be tapped")
    for i, title in enumerate(TEST_NETWORK_LABELS):
        if ui.on_window(title, timeout=8.0 if i == 0 else 2.0):
            return title
    # No navigation bar by either name. Accept the window only if the debugger
    # page itself is gone AND the network is drawn — a visible "Pangle" on
    # the debugger page would be its SDK-integrations row instead.
    if (not ui._ax_rect(ui.MAX_DEBUGGER, kind=None)
            and ui.scroll_to_text(network, max_swipes=SWIPES)):
        print(f"  no navigation bar named {TEST_NETWORK_LABELS}; the debugger "
              f"page is gone and {network!r} is drawn — taking that as the "
              f"network window")
        return "(untitled)"
    ui.expect(False,
              f"tapping {row_label!r} did not open the test-network window — "
              f"no navigation bar named {TEST_NETWORK_LABELS}. Still on the "
              f"debugger: {ui.on_max_debugger(timeout=1.0)}")


def _settled_network_rect(network: str = NETWORK):
    """Rect of the network row once the list has stopped and it is mid-screen.

    The list glides on after a swipe, and scroll_to_text() stops as soon as
    the row is visible — often half-drawn at the bottom edge, where a tap on
    its moving centre selected nothing.
    """
    if not ui.scroll_to_text(network, max_swipes=SWIPES):
        return None
    ui.sleep(1.5)
    height = ui.screen_size()[1] / ui._point_scale()
    rect = ui._ax_rect(network)
    if rect and rect["y"] + rect["height"] > 0.8 * height:
        ui.scroll(down=True, frac=0.25)
        ui.sleep(1.5)
        rect = ui._ax_rect(network)
    return rect


def _select_test_network(network: str = NETWORK):
    row_label, row_rect = _scroll_to_any(TEST_NETWORK_LABELS)
    ui.expect(row_label,
              f"never brought {TEST_NETWORK_ROW!r} or "
              f"{TEST_NETWORK_SELECTED!r} into view in {SWIPES} swipes (and a "
              f"reopen-from-the-top did not help) — Test Mode may be off")
    section = _shoot("ad_test_mode_section")
    print(f"  found {row_label!r} — see {section}")
    already_selected = _row_shows(network, row_rect)
    print(f"  {network} already shown on the test-network row: "
          f"{already_selected}")

    title = _open_test_network_window(row_label, row_rect, network)
    print(f"  test-network window open ({title!r})")
    # Reported every run rather than assumed: if something is already ticked,
    # the checkmark assertion below no longer proves this tap did anything.
    was_ticked = already_selected or bool(
        ui._ax_first("XCUIElementTypeButton", "checkmark", timeout=6.0))
    print(f"  a network was already selected before tapping: {was_ticked}")
    if already_selected:
        print(f"  keeping the existing {network} selection")
    ticked = already_selected
    for attempt in range(2 if not already_selected else 0):
        rect = _settled_network_rect(network)
        ui.expect(rect, f"{network!r} is not listed on the test-network "
                        f"window")
        ui.expect(_tap_rect(rect, settle=3.0),
                  f"{network!r} could not be tapped")
        text = ui.alert_now()
        if text:
            print(f"  pop-up after selecting {network}: {text!r} — pressing OK")
            ui.expect(_ok_alert(f"the pop-up after selecting {network}"),
                      f"could not dismiss the pop-up after selecting "
                      f"{network}: {text!r}")
        # The checkmark is a BUTTON that does not exist until something is
        # selected, so its appearance is the proof the tap registered.
        ticked = bool(ui._ax_first("XCUIElementTypeButton", "checkmark",
                                   timeout=8.0))
        if ticked:
            break
        print(f"  no checkmark after tapping {network} — tapping it again")
    ui.expect(ticked,
              f"tapping {network!r} did not select it — no checkmark appeared "
              f"on the test-network list")
    picked = _shoot(f"ad_{network.lower()}")
    print(f"  {network} selected (checkmark shown) — see {picked}")


def _back_out_of_subwindows(why: str = "") -> bool:
    for title in SUBWINDOWS:
        if ui.on_window(title, timeout=1.0):
            if why:
                print(f"  {why}: backing out of the {title!r} window")
            ui.expect(ui._tap_named("XCUIElementTypeButton", "BackButton"),
                      f"could not back out of the {title!r} window")
            ui.sleep(2)
            return True
    return False


def unwind_leftovers():
    """Clear what an interrupted run can leave over Spider, without relaunching.

    The one exception is MAX's restart alert: answering it means the relaunch
    it asks for must happen now.
    """
    leftover = ui.alert_now()
    if RESTART_TEXT in leftover.lower():
        print(f"  a previous run left MAX's restart pop-up up: {leftover!r}")
        ui.expect(_ok_alert("the leftover restart pop-up"),
                  "could not press OK on the leftover restart pop-up")
        _relaunch_to_menu("finishing an interrupted Test Mode restart")
    _back_out_of_subwindows("a previous run left a network window open")
    if ui.on_max_debugger(timeout=2.0):
        print("  a previous run left the debugger open — closing it first")
        ui.expect(ui.close_max_debugger(),
                  "the debugger was left open by an earlier run and will not "
                  "close; its 'Done' button is top-left ('Share' sits beside it)")


def close_overlays():
    """Leave the network window, the debugger and the Dev Panel overlay."""
    _back_out_of_subwindows()
    if ui.on_max_debugger(timeout=2.0):
        ui.expect(ui.close_max_debugger(),
                  "could not close the debugger; its 'Done' button is top-left "
                  "('Share' sits beside it)")
    if ui.dev_panel_open():
        ui.expect(ui.close_dev_panel(),
                  "could not collapse the Dev Panel overlay")


def ensure_network(network: str = NETWORK, capture: bool = True,
                   fresh: bool = True):
    """Dev Panel -> Max Debugger -> Test Mode on -> ``network`` ticked -> exit.

    ``fresh`` (the default) relaunches Spider FIRST and enables Test Mode in
    that new session, because a "Test Mode Enabled: true" reading proved
    stale once: after WDA crashed under a run, the debugger read true with
    Pangle ticked while every ad and banner came from live networks. A fresh
    session that still reads true is switched back to live (and restarted)
    before Test Mode is enabled again. Enabling relaunches Spider once more;
    the Dev Panel is unlocked again after each relaunch. Ends with the
    debugger closed and the Dev Panel collapsed, on About.
    """
    global CAPTURE, _KEPT, _BUSY
    CAPTURE = capture
    busy, _BUSY = _BUSY, True
    try:
        if fresh:
            _relaunch_to_menu("starting a fresh app session, so MAX Test Mode "
                              "is enabled in it rather than trusted from an "
                              "earlier reading")
        _open_debugger()
        on, evidence = _test_mode_state()
        ui.expect(on is not None,
                  f"cannot tell whether MAX Test Mode is on — {evidence}. The "
                  f"debugger's Ads section may have changed in this MAX SDK")
        print(f"  Test Mode on: {on} — {evidence}")
        if on and fresh:
            print("  a fresh session should read Test Mode off — switching it "
                  "back to live first, then enabling it again")
            _disable_test_mode_and_relaunch()
            on = False
        if not on:
            _enable_test_mode_and_relaunch()
        _select_test_network(network)
        ui.expect(_back_out_of_subwindows(),
                  "could not find the test-network window to back out of")
        ui.expect(ui.close_max_debugger(),
                  "could not close the debugger; its 'Done' button is top-left "
                  "('Share' sits beside it)")
        ui.expect(ui.close_dev_panel(),
                  "could not collapse the Dev Panel overlay — it covers the "
                  "menu labels, so on_menu()/open_picker() cannot see them")
    finally:
        CAPTURE = True
        _BUSY = busy
    _KEPT = network
    ui.on_relaunch(_after_relaunch)


def _after_relaunch():
    """Relaunch hook: Test Mode is off again, so turn it on before any ad."""
    global _BUSY
    if _KEPT is None or _BUSY:
        return
    print(f"  Spider was relaunched, which turns MAX Test Mode off — "
          f"re-enabling it on {_KEPT} before any ad can come from a live "
          f"network")
    _BUSY = True
    try:
        ensure_network(_KEPT, capture=False, fresh=False)
        ui.expect(ui.on_menu(timeout=4.0) or ui.to_menu(),
                  "could not get back to the main menu after re-enabling "
                  "MAX Test Mode")
    finally:
        _BUSY = False


def live_ad_served(where: str) -> str:
    """An ad closed without a test ad's controls: re-enable Test Mode.

    Returns the failure text for the caller to raise, so the check that saw
    the live ad fails by name while the run carries on in Test Mode.
    """
    taps = (ui.LAST_AD_CLOSE or {}).get("taps", [])
    network = _KEPT or NETWORK
    print(f"  LIVE ad at {where}: closed by {taps}, with no {network} skip "
          f"or X — MAX Test Mode was lost; re-enabling it")
    ensure_network(network, capture=False, fresh=True)
    return (f"a LIVE ad was served at {where} (closed by {taps}, not by "
            f"{network}'s skip or X) — MAX Test Mode had been lost; it has "
            f"been re-enabled on {network}")

