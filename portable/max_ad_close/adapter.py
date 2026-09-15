"""Hooks the other FingerArts / PeopleFun Unity project must supply.

MAX's Mediation Debugger and the StoreKit close button are native UIKit, so
those halves of this kit talk to WDA. Everything that is *the game* — whether
an ad is covering the UI, where a template matched, which bundle is in front —
comes through this adapter.

Construct one with callables (or plain values) from the other driver:

    from portable.max_ad_close import Adapter

    adapter = Adapter(
        session=helpers.current_session,
        wda_url=config.WDA_URL,
        bundle_id=config.BUNDLE_ID,
        find=ui.find,
        tap=ui.tap,
        tap_at=ui.tap_at,
        lost=ui.lost,
        in_app=ui.in_app,
        shoot=ui.shoot,
        screen_size=ui.screen_size,
        assets_dir=config.UNITY_ASSETS,
        active_app=ui.active_app,
        scroll=ui.scroll,                 # optional; kit can swipe via WDA
        reopen_max_debugger=reopen,       # optional; Done + tap Max Debugger
        close_dev_panel=ui.close_dev_panel,
    )
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional, Sequence, Tuple


Pos = Tuple[int, int]


def _invoke(value: Any, *args, **kwargs):
    """Call ``value`` if it is callable, otherwise return it as a constant."""
    return value(*args, **kwargs) if callable(value) else value


class Adapter:
    """Game-specific surface this kit cannot invent.

    Required:
        session, wda_url, bundle_id, find, tap, tap_at, lost, in_app,
        shoot, screen_size, assets_dir

    Optional:
        active_app, have, seen, scroll, expect, network_online,
        reopen_max_debugger, close_dev_panel, sleep, game_name
    """

    def __init__(
        self,
        *,
        session: Any,
        wda_url: Any,
        bundle_id: Any,
        find: Callable[[str], Optional[Pos]],
        tap: Callable[..., bool],
        tap_at: Callable[..., Any],
        lost: Callable[..., bool],
        in_app: Callable[..., bool],
        shoot: Callable[[str], str],
        screen_size: Callable[[], Sequence[int]],
        assets_dir: Any,
        active_app: Optional[Callable[[], str]] = None,
        have: Optional[Callable[[str], bool]] = None,
        seen: Optional[Callable[..., bool]] = None,
        scroll: Optional[Callable[..., Any]] = None,
        expect: Optional[Callable[[Any, str], Any]] = None,
        network_online: Optional[Any] = None,
        reopen_max_debugger: Optional[Callable[[], bool]] = None,
        close_dev_panel: Optional[Callable[..., bool]] = None,
        sleep: Optional[Callable[[float], Any]] = None,
        game_name: str = "the game",
    ):
        self._session = session
        self._wda_url = wda_url
        self._bundle_id = bundle_id
        self._find = find
        self._tap = tap
        self._tap_at = tap_at
        self._lost = lost
        self._in_app = in_app
        self._shoot = shoot
        self._screen_size = screen_size
        self._assets_dir = assets_dir
        self._active_app = active_app
        self._have = have
        self._seen = seen
        self._scroll = scroll
        self._expect = expect
        self._network_online = network_online
        self.reopen_max_debugger = reopen_max_debugger
        self.close_dev_panel = close_dev_panel
        self._sleep = sleep or time.sleep
        self.game_name = game_name

    def session(self) -> Optional[str]:
        return _invoke(self._session)

    def wda_url(self) -> str:
        return str(_invoke(self._wda_url)).rstrip("/")

    def bundle_id(self) -> str:
        return str(_invoke(self._bundle_id))

    def assets_dir(self) -> str:
        return str(_invoke(self._assets_dir))

    def find(self, name: str):
        return self._find(name)

    def tap(self, name: str, timeout: float = 8.0, settle: float = 1.5,
            reason: Optional[str] = None) -> bool:
        try:
            return bool(self._tap(name, timeout=timeout, settle=settle,
                                  reason=reason))
        except TypeError:
            return bool(self._tap(name, timeout=timeout, settle=settle))

    def tap_at(self, pos, settle: float = 1.2, reason: Optional[str] = None):
        try:
            return self._tap_at(pos, settle=settle, reason=reason)
        except TypeError:
            return self._tap_at(pos, settle=settle)

    def lost(self, timeout: float = 2.0) -> bool:
        return bool(self._lost(timeout=timeout))

    def in_app(self) -> bool:
        return bool(self._in_app())

    def shoot(self, name: str) -> str:
        return self._shoot(name)

    def screen_size(self):
        w, h = self._screen_size()
        return int(w), int(h)

    def active_app(self) -> str:
        if self._active_app is not None:
            return self._active_app() or ""
        return ""

    def have(self, name: str) -> bool:
        if self._have is not None:
            return bool(self._have(name))
        return os.path.exists(os.path.join(self.assets_dir(), name + ".png"))

    def seen(self, name: str, timeout: float = 8.0) -> bool:
        if self._seen is not None:
            try:
                return bool(self._seen(name, timeout=timeout))
            except TypeError:
                return bool(self._seen(name, timeout))
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.find(name) is not None:
                return True
            self.sleep(0.2)
        return False

    def scroll(self, down: bool = True):
        if self._scroll is None:
            raise RuntimeError(
                "adapter.scroll is not set and WdaAx.scroll was not used")
        try:
            return self._scroll(down=down)
        except TypeError:
            return self._scroll(down)

    def has_scroll(self) -> bool:
        return self._scroll is not None

    def expect(self, cond, msg: str):
        if self._expect is not None:
            return self._expect(cond, msg)
        if not cond:
            raise AssertionError(msg)
        return True

    def network_online(self):
        """True / False / None (unknown). None means 'do not block dismiss_ad'."""
        if self._network_online is None:
            return None
        return _invoke(self._network_online)

    def sleep(self, sec: float):
        self._sleep(sec)
