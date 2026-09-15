"""Close an AppLovin interstitial: StoreKit X first, then the ad's own X.

Lifted from unity_ui.py. Pinning AppLovin is what makes the second X appear —
without it, a 5-minute watch produced one StoreKit X and the game never came
back.

Never tap the moving ▶▶ skip glyph. It scores 0.65–0.75 on real ads and 0.656
on a plain menu.

Coordinate spaces: native Close is tapped in WDA POINTS. Template matches and
AD_CLOSE_COORDS are CAPTURE PIXELS, scaled from AD_CLOSE_REF_SIZE.
"""
from __future__ import annotations

import os
import time

from .adapter import Adapter
from .wda_ax import WdaAx

AD_CLOSERS = ("ad_store_close", "ad_close")

# StoreKit's product-sheet X, and some ad SDKs' own close, publish as a button
# named Close. Never include skip / "▶▶".
_CLOSE_AX = ("Close", "close")

# Capture-pixel centres for known iPhone-11 playable-ad X controls. These are
# reference coordinates, not blind first-choice taps: tap_ad_close() reaches
# them only after every creative crop failed, while the foreground is still
# the game, and accepts a tap only when the interstitial disappears. Add the
# centre here whenever a new ad_close*.png creative is added.
AD_CLOSE_COORDS = {
    "ad_close": (50, 136),
    "ad_close_creative_02": (55, 139),
    "ad_close_creative_03": (57, 145),
}
AD_CLOSE_REF_SIZE = (828, 1792)
# How far a crop match may sit from its registered centre. The false match that
# opened the App Store was ~1600 px away; real creatives stay in the top-left.
_AD_CLOSE_POS_TOL = 80

_KIT_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def kit_assets_dir() -> str:
    """Directory of the shipped ad_close*.png creatives."""
    return _KIT_ASSETS


def _ad_close_names(adapter: Adapter):
    """Stem names of every ad_close*.png in the adapter dir, then this kit."""
    seen = set()
    names = []
    for folder in (adapter.assets_dir(), _KIT_ASSETS):
        if not folder or not os.path.isdir(folder):
            continue
        for stem in sorted(os.listdir(folder)):
            if stem.startswith("ad_close") and stem.endswith(".png"):
                name = stem[:-4]
                if name not in seen:
                    seen.add(name)
                    names.append(name)
    return names


def _tap_ax_close(ax: WdaAx) -> bool:
    """Tap a native Close button if one is showing. Does not guess a position."""
    for name in _CLOSE_AX:
        if ax.tap_named("XCUIElementTypeButton", name):
            return True
    return False


def ad_close_pos_ok(adapter: Adapter, name: str, pos) -> bool:
    """True when a playable-ad X crop matched near its registered centre."""
    if name == "ad_store_close":
        return True
    if pos is None:
        return False
    known = AD_CLOSE_COORDS.get(name)
    if known is None:
        return False
    w, h = adapter.screen_size()
    rw, rh = AD_CLOSE_REF_SIZE
    expect_x = int(round(known[0] * w / rw))
    expect_y = int(round(known[1] * h / rh))
    return (abs(pos[0] - expect_x) <= _AD_CLOSE_POS_TOL
            and abs(pos[1] - expect_y) <= _AD_CLOSE_POS_TOL)


def wait_lost(adapter: Adapter, timeout: float = 20.0) -> bool:
    """True once an interstitial has covered the game's own UI, still in-app.

    False if we left the game (a tap that opened the real App Store) or if a
    recognisable screen is still showing when the budget runs out.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not adapter.in_app():
            return False
        if adapter.lost(timeout=1.0):
            return True
        adapter.sleep(1)
    return adapter.in_app() and adapter.lost(timeout=1.0)


def tap_store_close(adapter: Adapter, timeout: float = 90.0,
                    settle: float = 2.0) -> bool:
    """Wait for the in-app StoreKit product-sheet X and tap it.

    The sheet is native UIKit over the Unity view — foreground stays the game —
    so the close control is READ first (a button named Close), then matched as
    ad_store_close if a crop exists. Never a guessed corner: a miss taps the
    ad and can open the real App Store. The video plays ~15s then opens this
    sheet by itself; callers should wait, not tap skip.
    """
    ax = WdaAx(adapter)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _tap_ax_close(ax):
            adapter.sleep(settle)
            return True
        if adapter.have("ad_store_close") and adapter.seen("ad_store_close", timeout=1.0):
            if adapter.tap("ad_store_close", timeout=1.0, settle=settle,
                           reason="tap_store_close:ad_store_close"):
                return True
        adapter.sleep(1.5)
    return False


def tap_ad_close(adapter: Adapter, timeout: float = 30.0,
                 settle: float = 2.0) -> bool:
    """Wait for the interstitial's own X (after the store sheet) and tap it.

    Same order as tap_store_close: native Close first, then every
    ``ad_close*.png`` creative. Each playable creative can put the grey
    circular X over different artwork, so failed runs add a new crop instead
    of replacing an older one. The skip glyph is never a candidate.
    """
    ax = WdaAx(adapter)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _tap_ax_close(ax):
            adapter.sleep(settle)
            if not adapter.in_app():
                return False
            if not adapter.lost(timeout=1.0):
                return True
        for name in _ad_close_names(adapter):
            pos = adapter.find(name)
            if pos is not None and ad_close_pos_ok(adapter, name, pos):
                if adapter.tap(name, timeout=1.0, settle=settle,
                               reason=f"tap_ad_close:{name}"):
                    if not adapter.in_app():
                        return False
                    if not adapter.lost(timeout=1.0):
                        return True
        # A new creative can have a different background behind the same X,
        # making its crop unavailable even though the control is visible.
        # Coordinates are the guarded fallback, never the primary locator.
        if adapter.in_app() and adapter.lost(timeout=0.5):
            w, h = adapter.screen_size()
            rw, rh = AD_CLOSE_REF_SIZE
            for name, (x, y) in AD_CLOSE_COORDS.items():
                point = (int(round(x * w / rw)), int(round(y * h / rh)))
                adapter.tap_at(point, settle=settle, reason=f"tap_ad_close:coord:{name}")
                if not adapter.in_app():
                    return False
                if not adapter.lost(timeout=1.0):
                    return True
        adapter.sleep(1.5)
    # Preserve the creative BEFORE the caller raises and the ad has time to
    # dismiss itself. Crop a 54x54 RGB PNG from this frame if the X is new.
    if adapter.in_app() and adapter.lost(timeout=0.5):
        path = adapter.shoot("ad_unmatched")
        print(f"  unmatched ad close captured before failure — see {path}")
    elif adapter.in_app():
        # The ad may close itself at the edge of the timeout. That is a
        # successful return to the game, not an unmatched-close failure.
        return True
    return False


def close_interstitial_chain(adapter: Adapter, where: str = "interstitial",
                             store_timeout: float = 90.0,
                             ad_timeout: float = 30.0) -> bool:
    """Close the StoreKit product sheet first, then the ad's own X."""
    game = adapter.game_name
    adapter.expect(adapter.in_app(),
                   f"the interstitial took us out of {game} after "
                   f"{where} — now in {adapter.active_app() or 'unknown'}")
    adapter.expect(tap_store_close(adapter, timeout=store_timeout),
                   f"the App Store product sheet's X never appeared after {where} "
                   f"within {store_timeout:.0f}s")
    adapter.expect(tap_ad_close(adapter, timeout=ad_timeout),
                   f"the interstitial's own X never appeared after the StoreKit "
                   f"sheet closed ({where})")
    return True


def dismiss_ad(adapter: Adapter, timeout: float = 1.5) -> bool:
    """Close ONE layer of ad if a known close control is showing.

    A single close is not the same as "back in the game" — callers must loop
    and keep a time budget (see ad_free()). Never a guessed position.

    A playable-ad crop is rejected unless it matched near its registered
    centre. ``ad_close`` once scored a hit at (111, 1730) on first-launch
    chrome — that tap opened the real App Store.
    """
    if adapter.network_online() is False:
        # There is no live ad to dismiss in Airplane Mode. Hunting stale ad
        # crops here is dangerous: a false match can tap a real App Store link.
        return False
    if not adapter.lost(timeout=timeout):
        return False
    ax = WdaAx(adapter)
    if _tap_ax_close(ax):
        adapter.sleep(1.5)
        return True
    for name in AD_CLOSERS:
        if not adapter.have(name) and name not in _ad_close_names(adapter):
            continue
        pos = adapter.find(name)
        if pos is None or not ad_close_pos_ok(adapter, name, pos):
            continue
        if adapter.tap(name, settle=1.5, reason=f"dismiss_ad:{name}"):
            return True
    return False


def ad_free(adapter: Adapter, budget: float = 90.0) -> bool:
    """Clear ads until the game's own UI is back, or the budget runs out.

    For leftover/setup ads only. The assertion path that is waiting for an
    interstitial must NOT call this, or it swallows the ad under test.
    """
    deadline = time.time() + budget
    while time.time() < deadline:
        if not adapter.lost(timeout=1.0):
            return True
        if not dismiss_ad(adapter, timeout=1.0):
            adapter.sleep(2.0)
    return not adapter.lost(timeout=1.5)
