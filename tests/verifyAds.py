#!/usr/bin/env python3
"""Test: advertising still works. [UNITY]  *** NEEDS THE DEVICE ONLINE ***

Ads are the app's revenue, so a port that broke them is a serious regression —
and one the rest of this suite cannot see, because the rest of the suite runs
OFFLINE on purpose (ads interrupt screen transitions and make navigation tests
flaky). This test is the opposite: it needs the network, so it is NOT in
run_all.py's TESTS list. Run it deliberately, with the device online.

What it checks:
  1. a BANNER is being served on the main menu (and, if it rotates inside the
     sampling window, that it is live rather than a frozen leftover);
  2. an INTERSTITIAL appears where the app schedules one — leaving a game;
  3. the ad NEVER TAKES THE USER OUT OF SPIDER on its own. This is the assertion
     that matters most for stability: com.fingerarts.Spider must still be the
     foreground app the whole time;
  4. the app RECOVERS — after the ads are closed or finish, Spider's own UI is
     usable again and the menu is reachable.

Measured behaviour on build 353 / iPhone 11, which shapes the test:
  * Interstitials fire reliably on game exit — 12 of 12 attempts.
  * They render INSIDE the app; the foreground app stays Spider.
  * They CHAIN: a video interstitial plays ~15s, then at ~16s it opens an App
    Store product sheet BY ITSELF with no tap (confirmed with screenshot-only
    sampling, 40 frames, no touch events), and closing that sheet starts a
    further playable ad. So "close the ad" is a loop with a budget, not one tap.
  * THE CHAIN IS LONG. Watched for 5 minutes: only ONE closable control ever
    appeared (the store sheet's X, at t+27s) and Spider's own UI never came
    back on its own. A user with no relaunch button is stuck for minutes.
  * The only other way out is a small "▶▶" skip glyph, and this test does NOT
    use it: its position moves between creatives (top-left on some, top-right
    on others) and a crop of it scores 0.65-0.75 on real ads but 0.656 on the
    plain main menu, so it cannot be told from noise. Tapping near a guess would
    hit the ad and open the App Store.
  * Because creatives are third party and differ every run, this test reports
    what it could not dismiss instead of asserting on any one creative's close
    button. Only ad SERVING and app HEALTH are hard assertions.

Captures log/ad_banner_*.png, log/ad_interstitial.png, log/ad_recovered.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set, and the
device ONLINE (this is the one test that wants the network).
Run:  ./.venv/bin/python tests/verifyAds.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import unity_ui as ui  # noqa: E402

# The banner sits in a strip across the bottom. Fractions of screen height, so
# this holds on other devices too.
BANNER_TOP, BANNER_BOTTOM = 0.90, 0.98
ROTATE_WAIT = 14.0          # how long to watch for the banner to change
AD_BUDGET = 90.0            # how long an interstitial may hold the screen


def band(path, top=BANNER_TOP, bottom=BANNER_BOTTOM):
    import cv2
    img = cv2.imread(path, 0)
    if img is None:
        return None
    h = img.shape[0]
    return img[int(h * top):int(h * bottom)]


def band_diff(a, b):
    import numpy as np
    ba, bb = band(a), band(b)
    if ba is None or bb is None or ba.shape != bb.shape:
        return None
    return float(np.abs(ba.astype("int16") - bb.astype("int16")).mean())


def check_banner():
    """A banner is being served on the menu, and ideally is seen to rotate."""
    ui.expect(ui.on_menu(), "not on the main menu to look at the banner")
    first = ui.shoot("ad_banner_1")
    ui.sleep(ROTATE_WAIT)
    second = ui.shoot("ad_banner_2")

    delta = band_diff(first, second)
    ui.expect(delta is not None, "could not read the banner strip from the captures")
    if delta > 1.0:
        print(f"  banner is live — it changed within {ROTATE_WAIT:.0f}s "
              f"(mean delta {delta:.1f}) — see {first}, {second}")
    else:
        # Not a failure: a banner may simply hold one creative this long. Say so
        # rather than claiming more than was observed.
        print(f"  banner did not change within {ROTATE_WAIT:.0f}s (delta "
              f"{delta:.1f}) — serving not confirmed by rotation; see {first}")


def trigger_interstitial():
    """Deal a game and leave it — where the app schedules an interstitial."""
    ui.expect(ui.tap("menu_play", settle=2.5), "Play not found on the menu")
    ui.expect(ui.tap("difficulty_easy", settle=3.0), "Easy not found on the picker")
    ui.settle_prompts()
    ui.expect(ui.at_table(timeout=12.0), "could not deal a game to leave")
    ui.expect(ui.tap("back_game", settle=2.0), "the in-game back control was not found")
    ui.settle_prompts()


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    check_banner()

    trigger_interstitial()

    # 2. an interstitial took the screen. `lost()` means none of Spider's own
    #    landmarks are visible, which on this transition means an ad is up.
    showed = ui.lost(timeout=4.0)
    shot = ui.shoot("ad_interstitial")
    ui.expect(showed,
              "no interstitial appeared after leaving a game. Ads are revenue, so "
              "this is worth checking before dismissing it: confirm the device is "
              f"ONLINE (this test needs the network) and re-run. See {shot}")
    print(f"  interstitial appeared on leaving a game — see {shot}")

    # 3. the ad must not carry the user out of the app by itself.
    where = ui.active_app()
    ui.expect(where == config.BUNDLE_ID,
              f"the interstitial moved the user OUT of Spider on its own — the "
              f"foreground app is now {where or 'unknown'}. An ad may only leave "
              f"the app when the user taps it.")
    print("  the ad stays inside Spider (no unasked-for app switch)")

    # 4. the app comes back. Ads chain here (video -> auto store sheet ->
    #    playable), so this closes what is closable and waits out what is not.
    t0 = time.time()
    cleared = ui.ad_free(budget=AD_BUDGET)
    took = time.time() - t0
    if not cleared:
        # Third-party creatives vary run to run, so falling back to the
        # documented recovery is not a rig failure — but it IS worth reporting,
        # because a user has no relaunch button. Measured once at 5 minutes with
        # the ads still running, so do not read this as a slow-network blip.
        print(f"  WARNING: still on an ad after {AD_BUDGET:.0f}s with no close "
              f"control in reach — falling back to relaunch. Watched once for a "
              f"full 5 minutes and the app never came back on its own, so a real "
              f"user is stuck for minutes. Worth raising with the ad team. "
              f"See {ui.shoot('ad_stuck')}")
        ui.expect(ui.recover(), "could not recover the app after the interstitial")
    else:
        print(f"  ads cleared in {took:.0f}s without restarting the app")

    ui.expect(ui.active_app() == config.BUNDLE_ID,
              "Spider is not the foreground app after the ads")
    ui.expect(ui.to_menu(), "could not get back to the main menu after the ads")
    shot = ui.shoot("ad_recovered")
    ui.expect(ui.on_menu(), f"the menu is not usable after the ads — see {shot}")
    print(f"  the app is usable again afterwards — see {shot}")

    print("PASS: ads are being served, stay inside the app, and the app recovers")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
