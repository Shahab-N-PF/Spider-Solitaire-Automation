"""Small WDA helpers for installing Spider from TestFlight.

TestFlight is native UIKit, so its controls are read from WDA's accessibility
tree rather than from the Unity image templates.  The helpers deliberately
keep the current WDA session: launching TestFlight changes the foreground app,
but does not terminate Spider until the caller explicitly uninstalls it.
"""
import json
import re
import subprocess
import sys
import time
import urllib.request

import config
import helpers
import unity_ui as ui


TESTFLIGHT = "com.apple.TestFlight"
_VERSION_RE = re.compile(
    r"(?P<marketing>\d+(?:\.\d+){1,3})\s*\((?P<build>\d+)\)"
)
_GROUP_RE = re.compile(r"^\d+(?:\.\d+){1,3}")
_ACTION_NAMES = (
    "Install",
    "INSTALL",
    "Update",
    "UPDATE",
    "Install Build",
)
_APP_NAMES = (
    "Spider ▻ Solitaire",
    "Spider > Solitaire",
    "Spider Solitaire",
    "Spider",
)


def _records(kinds=None):
    """Return visible native elements as dictionaries with rects.

    TestFlight has used both cells and buttons for app/build rows across iOS
    releases.  Querying a small set of classes and checking ``visible`` avoids
    tapping an accessibility element that is present but scrolled off-screen.
    """
    sid = helpers.current_session()
    if not sid:
        return []
    kinds = kinds or (
        "XCUIElementTypeCell",
        "XCUIElementTypeButton",
        "XCUIElementTypeStaticText",
        "XCUIElementTypeLink",
    )
    records = []
    for kind in kinds:
        body = json.dumps({"using": "class name", "value": kind}).encode()
        try:
            req = urllib.request.Request(
                config.WDA_URL + f"/session/{sid}/elements",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            elements = json.load(urllib.request.urlopen(req, timeout=10)).get(
                "value"
            ) or []
        except Exception:  # noqa: BLE001
            continue
        for element in elements:
            eid = element.get("ELEMENT") or (
                list(element.values())[0] if element else None
            )
            if not eid:
                continue

            def attr(name):
                try:
                    return json.load(urllib.request.urlopen(
                        config.WDA_URL
                        + f"/session/{sid}/element/{eid}/attribute/{name}",
                        timeout=5,
                    )).get("value")
                except Exception:  # noqa: BLE001
                    return None

            visible = attr("visible")
            if visible is False or str(visible).lower() == "false":
                continue
            rect = attr("rect") or {}
            records.append({
                "id": eid,
                "kind": kind,
                "name": str(attr("name") or ""),
                "label": str(attr("label") or ""),
                "value": str(attr("value") or ""),
                "rect": rect,
            })
    return records


def _text(record):
    return " ".join(
        part.strip()
        for part in (record["name"], record["label"], record["value"])
        if part.strip()
    )


def _matching_records(pattern, kinds=None):
    regex = re.compile(pattern, re.IGNORECASE)
    return [
        record for record in _records(kinds)
        if regex.search(_text(record))
    ]


def _tap_record(record):
    rect = record.get("rect") or {}
    if not rect:
        return False
    return ui._tap_point(
        rect.get("x", 0) + rect.get("width", 0) / 2,
        rect.get("y", 0) + rect.get("height", 0) / 2,
    )


def _tap_label(label, timeout=8.0):
    """Tap the first visible native control whose text exactly matches label."""
    deadline = time.time() + timeout
    wanted = label.strip().casefold()
    # Most TestFlight controls publish a stable accessibility name.  A
    # predicate lookup is much faster than enumerating every static text in
    # the app-detail page (which can take tens of seconds while it is loading).
    for kind in (
        "XCUIElementTypeButton",
        "XCUIElementTypeStaticText",
        "XCUIElementTypeLink",
        "XCUIElementTypeCell",
    ):
        remaining = max(0.5, deadline - time.time())
        rect = ui._ax_rect(label, kind=kind, timeout=remaining)
        if rect:
            if ui._tap_point(
                    rect["x"] + rect["width"] / 2,
                    rect["y"] + rect["height"] / 2):
                time.sleep(1.5)
                return True

    # Fallback for a TestFlight/iOS version that exposes the title only in
    # label/value rather than name.  This path is intentionally last.
    while time.time() < deadline:
        for record in _records():
            if any(
                part.strip().casefold() == wanted
                for part in (record["name"], record["label"], record["value"])
            ):
                if _tap_record(record):
                    time.sleep(1.5)
                    return True
        time.sleep(0.5)
    return False


def _scroll(down=True, duration=0.7):
    """Scroll the native TestFlight view using WDA point coordinates.

    Airtest swipes use capture pixels, while WDA actions use points.  Sending
    the former directly to this UIKit screen can become a long press on the
    iPhone 11, so convert the device-independent capture band explicitly.
    """
    sid = helpers.current_session()
    if not sid:
        return False
    try:
        scale = ui.point_scale()
        width, height = ui.screen_size()
        x = width / 2 / scale
        first_y = height * (0.78 if down else 0.30) / scale
        last_y = height * (0.30 if down else 0.78) / scale
        body = json.dumps({"actions": [{
            "type": "pointer",
            "id": "testflight-scroll",
            "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0,
                 "x": int(x), "y": int(first_y)},
                {"type": "pointerDown", "button": 0},
                {"type": "pause", "duration": 100},
                {"type": "pointerMove", "duration": int(duration * 1000),
                 "x": int(x), "y": int(last_y)},
                {"type": "pointerUp", "button": 0},
            ],
        }]}).encode()
        req = urllib.request.Request(
            config.WDA_URL + f"/session/{sid}/actions",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=20)
        time.sleep(0.8)
        return True
    except Exception:  # noqa: BLE001
        return False


def app_installed():
    """Return ``(marketing_version, build_number)`` or ``("", None)``.

    Return ``None`` when the device query itself failed.  That distinction is
    important: an unreadable device must never be treated as permission to
    uninstall the currently installed game.
    """
    cmd = [sys.executable, "-m", "tidevice"]
    if config.DEVICE_UDID:
        cmd += ["--udid", config.DEVICE_UDID]
    cmd += ["appinfo", "--json", config.BUNDLE_ID]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
        info = json.loads(result.stdout)
        if not isinstance(info, dict):
            raise ValueError("unexpected appinfo response")
    except (OSError, ValueError, subprocess.SubprocessError):
        # appinfo exits non-zero for an absent app.  Confirm that interpretation
        # with applist instead of confusing it with a disconnected device.
        list_cmd = [sys.executable, "-m", "tidevice"]
        if config.DEVICE_UDID:
            list_cmd += ["--udid", config.DEVICE_UDID]
        list_cmd += ["applist"]
        try:
            listed = subprocess.run(
                list_cmd, capture_output=True, text=True, timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if listed.returncode:
            return None
        for line in listed.stdout.splitlines():
            if line.split()[:1] == [config.BUNDLE_ID]:
                return "", None
        return "", None

    marketing = ""
    build = None
    for key in ("CFBundleShortVersionString", "CFBundleVersion"):
        if info.get(key):
            if key == "CFBundleShortVersionString":
                marketing = str(info[key])
            else:
                try:
                    build = int(str(info[key]).split(".", 1)[0])
                except ValueError:
                    pass
    return marketing, build


def uninstall_spider(timeout=45.0):
    """Uninstall Spider and wait until the device no longer reports it."""
    installed = app_installed()
    if installed is None:
        raise RuntimeError(
            "could not determine whether Spider is installed; "
            "check the USB connection and tidevice"
        )
    if installed == ("", None):
        return True
    cmd = [sys.executable, "-m", "tidevice"]
    if config.DEVICE_UDID:
        cmd += ["--udid", config.DEVICE_UDID]
    cmd += ["uninstall", config.BUNDLE_ID]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"could not uninstall {config.BUNDLE_ID}: "
            f"{detail or f'exit {result.returncode}'}"
        )
    deadline = time.time() + timeout
    while time.time() < deadline:
        if app_installed() == ("", None):
            return True
        time.sleep(1.0)
    return False


def open_testflight():
    """Foreground TestFlight and select its Apps tab when available."""
    try:
        helpers.launch_app(TESTFLIGHT, force=True, timeout=60)
    except Exception as exc:
        raise RuntimeError(
            "could not open TestFlight; install it and sign in on the device"
        ) from exc
    ui.connect()
    # TestFlight can reopen on the last detail page.  The Apps tab is the
    # stable way back to the list, and is harmless when already selected.
    _tap_label("Apps", timeout=4.0)
    return True


def open_spider(timeout=30.0):
    """Find the exact Spider app in TestFlight and open its detail page."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for name in _APP_NAMES:
            remaining = max(0.5, deadline - time.time())
            if _tap_label(name, timeout=min(3.0, remaining)):
                return name
        _scroll(down=True)
    return ""


def open_previous_builds(timeout=35.0):
    """Scroll the app detail page to Previous Builds and open it."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _tap_label("Previous Builds", timeout=1.0):
            return True
        _scroll(down=True)
    return False


def parse_build(text):
    """Return ``(marketing_version, build_number)`` from a TestFlight label."""
    normalized = re.sub(r"\s*\.\s*", ".", text or "")
    normalized = re.sub(r"\s+", " ", normalized)
    match = _VERSION_RE.search(normalized)
    if not match:
        return "", None
    return match.group("marketing"), int(match.group("build"))


def tap_newest_build(timeout=90.0):
    """Open the top version group, then tap its newest individual build."""
    deadline = time.time() + timeout
    opened_group = False
    while time.time() < deadline:
        candidates = []
        for record in _records((
            "XCUIElementTypeCell",
            "XCUIElementTypeButton",
            "XCUIElementTypeStaticText",
        )):
            marketing, build = parse_build(_text(record))
            if build is None:
                continue
            rect = record.get("rect") or {}
            if rect:
                candidates.append((float(rect.get("y", 10**9)),
                                   marketing, build, record))
        if candidates:
            _, marketing, build, record = min(candidates, key=lambda item: item[0])
            if _tap_record(record):
                time.sleep(2.5)
                return marketing, build

        # TestFlight first shows version groups ("8.0.2 — 5 Builds"). Open
        # the top group before looking for labels containing a build number.
        if not opened_group:
            groups = []
            for record in _records((
                "XCUIElementTypeCell",
                "XCUIElementTypeButton",
                "XCUIElementTypeStaticText",
            )):
                text = _text(record)
                normalized = re.sub(r"\s*\.\s*", ".", text).strip()
                if not _GROUP_RE.match(normalized):
                    continue
                rect = record.get("rect") or {}
                if rect:
                    groups.append((float(rect.get("y", 10**9)), record))
            if groups:
                _, record = min(groups, key=lambda item: item[0])
                if _tap_record(record):
                    opened_group = True
                    time.sleep(2.5)
                    continue
        _scroll(down=True)
    return "", None


def install_current_build(marketing, build, timeout=600.0):
    """Tap Install for the selected build and verify its installed build."""
    deadline = time.time() + timeout
    tapped = False
    while time.time() < deadline:
        installed = app_installed()
        if installed is None:
            time.sleep(3.0)
            continue
        current_marketing, current_build = installed
        if current_build == build:
            return True
        if not tapped:
            for action in _ACTION_NAMES:
                if _tap_label(action, timeout=1.0):
                    tapped = True
                    break
        if tapped:
            installed = app_installed()
            if installed is None:
                time.sleep(3.0)
                continue
            current_marketing, current_build = installed
            if current_build == build:
                return True
        time.sleep(3.0)
    return False
