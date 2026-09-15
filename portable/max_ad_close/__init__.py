"""Portable AppLovin pin + interstitial close kit.

Copy this folder into another FingerArts / PeopleFun Unity Airtest project,
implement Adapter against that driver, then:

    pin_applovin(adapter)                 # Max Debugger must already be open
    wait_lost(adapter)
    close_interstitial_chain(adapter, "leaving the game")

See README.md for the full journey. When tap_ad_close cannot match the
ad's own X, follow skills/capture-ad-close/SKILL.md — do not guess a
corner and do not cold-launch.
"""
from .adapter import Adapter
from .closer import (
    AD_CLOSE_COORDS,
    AD_CLOSE_REF_SIZE,
    ad_free,
    close_interstitial_chain,
    dismiss_ad,
    kit_assets_dir,
    tap_ad_close,
    tap_store_close,
    wait_lost,
)
from .pin_applovin import (
    LIVE_NETWORK,
    LIVE_NETWORK_SELECTED,
    NETWORK,
    close_debugger_overlays,
    pin_applovin,
)
from .wda_ax import MAX_DEBUGGER, WdaAx

__all__ = [
    "AD_CLOSE_COORDS",
    "AD_CLOSE_REF_SIZE",
    "Adapter",
    "LIVE_NETWORK",
    "LIVE_NETWORK_SELECTED",
    "MAX_DEBUGGER",
    "NETWORK",
    "WdaAx",
    "ad_free",
    "close_debugger_overlays",
    "close_interstitial_chain",
    "dismiss_ad",
    "kit_assets_dir",
    "pin_applovin",
    "tap_ad_close",
    "tap_store_close",
    "wait_lost",
]
