"""Pin AppLovin as the MAX live network.

The other project only has to get **Max Debugger** on screen (Dev Panel unlock
is game-specific). After that this module is WDA-only.

Lifted from tests/verifyAds.py. Traps that are load-bearing:

* The Ads row reads "Select Live Network" when empty and "Live Network" once a
  choice is persisted. Search for either, and only while VISIBLE.
* "AppLovin" also appears under Completed SDK Integrations on the debugger
  page. Confirm the picker NAVIGATION BAR before looking for the name.
* The checkmark button does not exist until a network is selected. Row text
  does not change, so the text alone proves nothing.
* Scroll is one direction. If Ads is above the viewport, Done + reopen from
  the top (adapter.reopen_max_debugger) rather than more down-swipes.
* Never cold-launch after this succeeds — a restart re-locks the Dev Panel
  and drops the selection.
"""
from __future__ import annotations

from typing import Optional

from .adapter import Adapter
from .wda_ax import MAX_DEBUGGER, WdaAx

LIVE_NETWORK = "Select Live Network"
LIVE_NETWORK_SELECTED = "Live Network"
NETWORK = "AppLovin"
SWIPES = 8


def visible_live_network_row(ax: WdaAx):
    """Visible debugger row label for live-network selection, or None."""
    for label in (LIVE_NETWORK, LIVE_NETWORK_SELECTED):
        if ax.rect(label):
            return label
    return None


def scroll_to_live_network(ax: WdaAx, max_swipes: int = SWIPES):
    """Scroll until either unselected or selected live-network row is visible."""
    for _ in range(max_swipes):
        label = visible_live_network_row(ax)
        if label:
            return label
        ax.scroll(down=True)
    return visible_live_network_row(ax)


def live_network_is(ax: WdaAx, network: str, row_label: str) -> bool:
    """True when the debugger's visible Live Network row shows ``network``."""
    live = ax.rect(row_label)
    selected = ax.rect(network)
    if not live or not selected:
        return False
    live_y = live["y"] + live["height"] / 2
    selected_y = selected["y"] + selected["height"] / 2
    return abs(live_y - selected_y) <= max(
        live["height"], selected["height"], 24)


def close_debugger_overlays(adapter: Adapter, ax: Optional[WdaAx] = None) -> None:
    """Leave leftover native overlays without restarting the game."""
    ax = ax or WdaAx(adapter)
    if ax.on_window(LIVE_NETWORK, timeout=2.0):
        adapter.expect(ax.tap_named("XCUIElementTypeButton", "BackButton"),
                       f"could not back out of the {LIVE_NETWORK!r} window")
        adapter.sleep(2)
    if ax.on_max_debugger(timeout=2.0):
        adapter.expect(ax.close_max_debugger(),
                       "could not close the debugger; its 'Done' button is "
                       "top-left ('Share' sits beside it)")
    if adapter.close_dev_panel is not None:
        adapter.expect(adapter.close_dev_panel(),
                       "could not collapse the Dev Panel overlay")


def pin_applovin(adapter: Adapter, network: str = NETWORK,
                 max_swipes: int = SWIPES) -> str:
    """Select ``network`` as the live network. Returns the network name.

    Requires MAX Mediation Debugger already open. Does not unlock the Dev
    Panel and does not tap Max Debugger — those stay in the other driver.
    """
    ax = WdaAx(adapter)
    adapter.expect(ax.on_max_debugger(),
                   f"{MAX_DEBUGGER!r} is not in the accessibility tree. "
                   "Open Max Debugger first.")

    row_label = scroll_to_live_network(ax, max_swipes=max_swipes)
    if not row_label and adapter.reopen_max_debugger is not None:
        print("  Ads section not in view — reopening the debugger from the top")
        adapter.expect(ax.close_max_debugger(),
                       "could not close the debugger to reset its scroll")
        adapter.expect(adapter.reopen_max_debugger(),
                       "could not reopen Max Debugger after a failed scroll")
        adapter.expect(ax.on_max_debugger(),
                       "reopening Max Debugger did not bring it back")
        row_label = scroll_to_live_network(ax, max_swipes=max_swipes)
    adapter.expect(row_label,
                   f"never brought {LIVE_NETWORK!r} or "
                   f"{LIVE_NETWORK_SELECTED!r} into view in {max_swipes} swipes"
                   f"{' (and a reopen-from-the-top did not help)' if adapter.reopen_max_debugger else ''}. "
                   "It lives in the debugger's 'Ads' section — if the row is "
                   "in the tree but never becomes visible, the list did not scroll.")
    print(f"  scrolled to the Ads section; found {row_label!r}")

    already_selected = live_network_is(ax, network, row_label)
    print(f"  {network} already shown on the Live Network row: {already_selected}")

    adapter.expect(ax.tap_text(row_label), f"{row_label!r} could not be tapped")
    adapter.expect(ax.on_window(LIVE_NETWORK),
                   f"tapping {row_label!r} did not open the {LIVE_NETWORK!r} "
                   f"window — no navigation bar by that name. Still on the "
                   f"debugger: {ax.on_max_debugger(timeout=1.0)}")
    print(f"  {LIVE_NETWORK!r} window opened")

    adapter.expect(ax.rect(network),
                   f"{network!r} is not listed on the {LIVE_NETWORK!r} window")
    was_ticked = already_selected or bool(
        ax.first("XCUIElementTypeButton", "checkmark", timeout=6.0))
    print(f"  a network was already selected before tapping: {was_ticked}")
    if not already_selected:
        adapter.expect(ax.tap_text(network, settle=3.0),
                       f"{network!r} could not be tapped")
    else:
        print(f"  keeping the existing {network} selection")

    adapter.expect(ax.first("XCUIElementTypeButton", "checkmark", timeout=8.0),
                   f"tapping {network!r} did not select it — no checkmark "
                   f"appeared on the {LIVE_NETWORK!r} list")
    print(f"  {network} selected (checkmark shown)")

    adapter.expect(ax.tap_named("XCUIElementTypeButton", "BackButton"),
                   f"could not back out of the {LIVE_NETWORK!r} window")
    adapter.sleep(2)
    adapter.expect(ax.close_max_debugger(),
                   "could not close the debugger; its 'Done' button is "
                   "top-left ('Share' sits beside it)")
    if adapter.close_dev_panel is not None:
        adapter.expect(adapter.close_dev_panel(),
                       "could not collapse the Dev Panel overlay — it covers "
                       "game labels, so menu/table checks cannot see them")
    return network
