"""WDA accessibility helpers for MAX's debugger and native Close buttons.

Lifted from unity_ui.py. Two rules that made the original flaky when ignored:

1. Ask for ONE element with a predicate (``name == '…'``). Enumerating the
   debugger's StaticTexts by class timed out at 15s and reported "no elements"
   on a screen that was plainly up.
2. Filter by ``kind`` after the predicate. The same name exists as a
   StaticText and as a NavigationBar ("Select Live Network"). Ignoring class
   made on_window() pass while still on the debugger page.

Element rects are WDA POINTS. Template matches are CAPTURE PIXELS. Anything
derived from a rect must go through tap_point() (W3C actions in point space),
never the game's capture-space tap_at(). Mixing them lands at half position
and reports success.
"""
from __future__ import annotations

import json
import time
import urllib.request

from .adapter import Adapter

MAX_DEBUGGER = "MAX Mediation Debugger"


class WdaAx:
    def __init__(self, adapter: Adapter):
        self.a = adapter

    def _get(self, path: str, timeout: float = 8.0):
        url = self.a.wda_url() + path
        return json.load(urllib.request.urlopen(url, timeout=timeout))

    def _post(self, path: str, body: dict, timeout: float = 10.0):
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            self.a.wda_url() + path, data=data,
            headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=timeout))

    def first(self, kind: str, name: str, timeout: float = 20.0):
        """Element id of the FIRST ``kind`` element called ``name``, or None.

        The ``kind`` filter is load-bearing: MAX's debugger page carries a
        static text reading "Select Live Network", and so does the navigation
        bar of the window that row opens.
        """
        sid = self.a.session()
        if not sid:
            return None
        escaped = name.replace("'", "\\'")
        try:
            payload = self._post(
                f"/session/{sid}/elements",
                {"using": "predicate string", "value": f"name == '{escaped}'"},
                timeout=timeout)
            for el in payload.get("value") or []:
                eid = el.get("ELEMENT") or (list(el.values())[0] if el else None)
                if not eid:
                    continue
                if kind:
                    try:
                        got = self._get(
                            f"/session/{sid}/element/{eid}/attribute/type",
                            timeout=8).get("value")
                    except Exception:  # noqa: BLE001
                        continue
                    if got != kind:
                        continue
                return eid
        except Exception:  # noqa: BLE001
            pass
        return None

    def attr(self, eid: str, name: str, timeout: float = 8.0):
        sid = self.a.session()
        return self._get(
            f"/session/{sid}/element/{eid}/attribute/{name}",
            timeout=timeout).get("value")

    def rect(self, name: str, kind: str = "XCUIElementTypeStaticText",
             visible_only: bool = True, timeout: float = 20.0):
        """Rect of the element called ``name``, or None.

        VISIBILITY IS THE POINT. MAX's debugger publishes rows that are scrolled
        out of view, and the rects it reports for them are nonsense — "Select
        Live Network" read y=102 while off screen, and "AppLovin" read y=-409.
        Tapping either would hit the wrong thing. The ``visible`` attribute is
        the only reliable signal that a row is actually drawn.
        """
        sid = self.a.session()
        if not sid:
            return None
        escaped = name.replace("'", "\\'")
        try:
            payload = self._post(
                f"/session/{sid}/elements",
                {"using": "predicate string", "value": f"name == '{escaped}'"},
                timeout=timeout)
            for el in payload.get("value") or []:
                eid = el.get("ELEMENT") or (list(el.values())[0] if el else None)
                if not eid:
                    continue
                try:
                    if kind and self.attr(eid, "type") != kind:
                        continue
                    if visible_only and self.attr(eid, "visible") is not True:
                        continue
                    rect = self.attr(eid, "rect") or {}
                except Exception:  # noqa: BLE001
                    continue
                if rect:
                    return rect
        except Exception:  # noqa: BLE001
            pass
        return None

    def tap_point(self, x: float, y: float) -> bool:
        """Tap a WDA POINT coordinate (not a capture-space one) via W3C actions."""
        sid = self.a.session()
        if not sid:
            return False
        body = {"actions": [{
            "type": "pointer", "id": "f1",
            "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0, "x": int(x), "y": int(y)},
                {"type": "pointerDown", "button": 0},
                {"type": "pause", "duration": 100},
                {"type": "pointerUp", "button": 0},
            ]}]}
        try:
            self._post(f"/session/{sid}/actions", body, timeout=10)
            return True
        except Exception:  # noqa: BLE001
            return False

    def tap_named(self, kind: str, name: str) -> bool:
        """Tap the element of ``kind`` called ``name`` at its rect centre.

        Taps the CENTRE rather than calling /element/<id>/click — click is not
        reliable on every iOS control (it can return success and do nothing).
        A coordinate tap derived from the element's own rect is still not a
        hardcoded position.
        """
        sid = self.a.session()
        eid = self.first(kind, name)
        if not eid:
            return False
        try:
            rect = self._get(
                f"/session/{sid}/element/{eid}/rect", timeout=8
            ).get("value") or {}
            ok = self.tap_point(
                rect["x"] + rect["width"] / 2,
                rect["y"] + rect["height"] / 2)
            return ok
        except Exception:  # noqa: BLE001
            return False

    def tap_text(self, name: str, kind: str = "XCUIElementTypeStaticText",
                 settle: float = 2.5) -> bool:
        """Tap the VISIBLE native element called ``name``."""
        rect = self.rect(name, kind)
        if not rect:
            return False
        ok = self.tap_point(
            rect["x"] + rect["width"] / 2,
            rect["y"] + rect["height"] / 2)
        if ok:
            self.a.sleep(settle)
        return ok

    def window_size(self):
        """WDA window size in POINTS, or None."""
        sid = self.a.session()
        if not sid:
            return None
        try:
            return self._get(f"/session/{sid}/window/size", timeout=15).get("value")
        except Exception:  # noqa: BLE001
            return None

    def scroll(self, down: bool = True, frac: float = 0.45,
               duration: float = 0.4):
        """Swipe the native list in POINT space. One direction only.

        If adapter.scroll is set, that is used instead (the game's content-band
        swipe). Otherwise this uses the WDA window size so the kit does not
        need Airtest swipe.
        """
        if self.a.has_scroll():
            self.a.scroll(down=down)
            return
        size = self.window_size()
        if not size:
            raise RuntimeError("cannot scroll: no adapter.scroll and no WDA window size")
        sid = self.a.session()
        w, h = int(size["width"]), int(size["height"])
        x = w // 2
        top, bottom = int(h * 0.30), int(h * 0.78)
        span = int(h * frac)
        start = (x, bottom) if down else (x, top)
        end = (x, bottom - span) if down else (x, top + span)
        ms = int(duration * 1000)
        body = {"actions": [{
            "type": "pointer", "id": "f1",
            "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0, "x": start[0], "y": start[1]},
                {"type": "pointerDown", "button": 0},
                {"type": "pointerMove", "duration": ms, "x": end[0], "y": end[1]},
                {"type": "pointerUp", "button": 0},
            ]}]}
        self._post(f"/session/{sid}/actions", body, timeout=15)
        self.a.sleep(0.8)

    def scroll_to_text(self, name: str, max_swipes: int = 10,
                       kind: str = "XCUIElementTypeStaticText") -> bool:
        """Scroll until ``name`` is actually VISIBLE. Not the same as present.

        ONE DIRECTION ONLY. If the target is ABOVE the current viewport this
        scrolls further away. Callers that cannot guarantee starting at the top
        should reopen the list rather than rely on this.
        """
        for _ in range(max_swipes):
            if self.rect(name, kind):
                return True
            self.scroll(down=True)
        return self.rect(name, kind) is not None

    def on_window(self, title: str, timeout: float = 8.0) -> bool:
        """True while a native window with this NAVIGATION BAR title is up.

        The bar is the discriminator, not a label: after "Select Live Network"
        is tapped, BOTH the old page's row and the new page's heading are
        static texts reading "Select Live Network".
        """
        deadline = time.time() + timeout
        while True:
            if self.first("XCUIElementTypeNavigationBar", title, timeout=8.0):
                return True
            if time.time() >= deadline:
                return False
            self.a.sleep(1)

    def on_max_debugger(self, timeout: float = 12.0) -> bool:
        """True once MAX's mediation debugger overlay is up.

        Identified by its TITLE. On screen it is truncated to
        "MAX Mediation Debug..." while the accessibility name carries the
        whole string — which is why this reads text rather than matching pixels.
        """
        deadline = time.time() + timeout
        while True:
            if self.first("XCUIElementTypeStaticText", MAX_DEBUGGER, timeout=8.0):
                return True
            if time.time() >= deadline:
                return False
            self.a.sleep(1)

    def close_max_debugger(self, timeout: float = 10.0) -> bool:
        """Dismiss the debugger with its own Done button. Never Share."""
        if not self.on_max_debugger(timeout=1.0):
            return True
        if not self.tap_named("XCUIElementTypeButton", "Done"):
            return False
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.on_max_debugger(timeout=1.0):
                return True
            self.a.sleep(1)
        return False
