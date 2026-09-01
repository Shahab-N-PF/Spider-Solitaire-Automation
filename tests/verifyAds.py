#!/usr/bin/env python3
"""Test: reach MAX's Mediation Debugger from the Dev Panel. [UNITY]

*** NEEDS THE DEVICE ONLINE — and this test puts it online itself. ***

**Chunks 1-2 of a rebuild.** verifyAds is being rebuilt around the Dev Panel's
"Max Debugger" — AppLovin MAX's own mediation debugger — instead of watching
banners and interstitials from the outside. So far: online, into the app, into
the Dev Panel whether or not it was already unlocked, into the debugger, then
down to its **Ads** section, into **Select Live Network**, and **AppLovin**
selected as the live network.

**IT ENDS THERE ON PURPOSE**, two screens deep, so the next chunk can carry on
from that screen — it does NOT return to the menu. The cost is that a re-run
starts behind those overlays, so step 2 unwinds them: back out of the Select
Live Network window, then close the debugger. Without that, launch_to_menu()
would fall through to cold_launch(), which RE-LOCKS the Dev Panel and would
leave the already-unlocked branch never exercised again.

Still NOT in run_all.py's TESTS: the suite runs offline on purpose (ads
interrupt screen transitions and make navigation flaky), and this needs the
network.

WHY THE DEBUGGER IS READ, NOT MATCHED. It is native UIKit drawn over the Unity
view — the foreground app stays com.fingerarts.Spider — so unlike the game it
publishes a real accessibility tree. Its title is the anchor. Measured on build
363 it lists Bundle ID com.fingerarts.Spider, App Version 8.0.0, OS iOS 26.5,
Account 9441, Mediation Provider max, MAX SDK 13.6.2, Plugin Max-Unity-8.6.3,
Unity 6000.0.73f1, then every integrated ad network.

Three things measured here that shape the code:
  * The debugger's table is BIG, and enumerating its elements by class TIMED OUT
    at 15s — which the element reader reports as "no elements", so a screen that
    was plainly up read as absent. Everything here uses targeted predicate
    queries (ui._ax_first), which answer the same question in ~1.1s.
  * Its on-screen title is truncated to "MAX Mediation Debug..." while the
    accessibility name carries the whole string. Another reason to read text
    rather than crop the header.
  * Rows scrolled out of view stay in the tree with UNTAPPABLE rects — "Select
    Live Network" reads y=102 while off screen and "AppLovin" reads y=-409. Only
    the `visible` attribute says a row is really drawn, which is why the scroll
    waits for visibility rather than presence (ui.scroll_to_text).

"AppLovin" IS AMBIGUOUS BY NAME. It appears on the debugger's own page under
"Completed SDK Integrations" as well as on the Select Live Network list — it is
in the tree before that window is ever opened. So the window is confirmed FIRST,
by its navigation bar, and only then is AppLovin looked for. The navigation bar
is the discriminator because both screens also carry a static text reading
"Select Live Network".

Captures log/ad_ads_section.png and log/ad_applovin.png as well.

WHAT EARLIER WORK ESTABLISHED, kept because later chunks rebuild on it (the
banner/interstitial version of this test is in git history):
  * interstitials fire on leaving a game — 12 of 12 attempts — and render
    INSIDE the app; the foreground app stays Spider;
  * they CHAIN: a video plays ~15s, then opens an App Store product sheet BY
    ITSELF with no tap (confirmed with screenshot-only sampling, 40 frames, no
    touch events), and closing that starts a further playable ad;
  * watched for a full 5 minutes, only ONE closable control ever appeared (the
    sheet's X, at t+27s) and Spider's own UI never came back on its own;
  * the "▶▶" skip glyph is deliberately NOT templated: its position moves
    between creatives and a crop scores 0.65-0.75 on real ads but 0.656 on the
    plain main menu, so it cannot be told from noise.
ui.ad_free() / ui.lost() / ui.recover() / ui.dismiss_ad() are kept for those.

Captures log/ad_dev_panel.png and log/ad_max_debugger.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
         The device may start offline — this test brings it online.
Run:  ./.venv/bin/python tests/verifyAds.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

BUTTON = "dev_max_debugger"
LIVE_NETWORK = "Select Live Network"
NETWORK = "AppLovin"
SWIPES = 8


def run():
    # 1. Make the device online rather than demanding it. One Settings visit
    #    toggles and waits for Wi-Fi to rejoin; it is a cheap no-op when the
    #    phone is already online.
    net = ui.online()
    ui.expect(net,
              "the device could not be brought online — Airplane Mode is off or "
              "could not be read, but Wi-Fi never rejoined a network. MAX needs "
              "the network to have anything to report.")
    print(f"  device is online — Wi-Fi joined {net!r}")

    # 2. Into the app. This run ENDS on the debugger by design, so a re-run
    #    starts behind that overlay — close it first. launch_to_menu() would not
    #    hard-fail there (it falls through to cold_launch), but that is the wrong
    #    outcome twice over: it costs a terminate+relaunch, and a restart
    #    RE-LOCKS the Dev Panel, so every re-run would silently exercise only the
    #    unlock branch and never the already-unlocked one.
    #    A run now ends TWO screens deep (the debugger, then Select Live
    #    Network), so recovery unwinds both — back out of the child window
    #    first, or close_max_debugger() finds no Done button and gives up.
    if ui.on_window(LIVE_NETWORK, timeout=2.0):
        print(f"  a previous run left the {LIVE_NETWORK!r} window open — backing out")
        ui.expect(ui._tap_named("XCUIElementTypeButton", "BackButton"),
                  f"could not back out of the {LIVE_NETWORK!r} window left open "
                  f"by an earlier run")
        ui.sleep(2)
    if ui.on_max_debugger(timeout=2.0):
        print("  a previous run left the debugger open — closing it first")
        ui.expect(ui.close_max_debugger(),
                  "the debugger was left open by an earlier run and will not "
                  "close; its 'Done' button is top-left ('Share' sits beside it)")
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")

    # 3. Into the Dev Panel. ONE call covers both cases the requirement names:
    #    already unlocked -> just expand it; not unlocked -> go to About, fire
    #    the 5 rapid taps on the spider emblem, then expand. Both are idempotent.
    ui.expect(ui.open_dev_panel(),
              "could not open the Dev Panel. It is revealed by 5 RAPID TAPS on "
              "the About screen's spider emblem (the emblem, not the wordmark "
              "below it — the wordmark is inert), and the gesture TOGGLES, so a "
              "second burst hides it again.")

    # 4. The button's presence is asserted separately from tapping it, so
    #    "the panel did not open" and "Max Debugger is gone from the panel"
    #    stay two different failures.
    ui.expect(ui.is_on(BUTTON),
              "the Dev Panel opened but has no 'Max Debugger' button — the "
              "panel's contents may have changed in this build")
    panel = ui.shoot("ad_dev_panel")
    print(f"  Dev Panel is open and offers Max Debugger — see {panel}")

    # 5-6. Open the debugger and STAY ON IT. Chunk 2 continues from here, so this
    #      deliberately does not dismiss it and does not return to the menu.
    ui.expect(ui.tap(BUTTON, settle=4.0), "the 'Max Debugger' button could not be tapped")
    ui.expect(ui.on_max_debugger(),
              f"tapping 'Max Debugger' did not open MAX's mediation debugger "
              f"— {ui.MAX_DEBUGGER!r} is not in the accessibility tree. The "
              f"foreground app is {ui.active_app() or 'unknown'}.")
    shot = ui.shoot("ad_max_debugger")
    print(f"  MAX Mediation Debugger is open — see {shot}")

    # ── chunk 2 ──────────────────────────────────────────────────
    # 7. The Ads section is below the fold. Scroll until the row is VISIBLE, not
    #    merely present: it is in the accessibility tree the whole time, off
    #    screen, reporting a rect (y=102) that cannot be tapped.
    reached = ui.scroll_to_text(LIVE_NETWORK, max_swipes=SWIPES)
    ui.expect(reached,
              f"never brought {LIVE_NETWORK!r} into view in {SWIPES} swipes. It "
              f"lives in the debugger's 'Ads' section, one swipe down on an "
              f"iPhone 11 — if the row is in the tree but never becomes visible, "
              f"the list did not scroll.")
    ads = ui.shoot("ad_ads_section")
    print(f"  scrolled to the Ads section — see {ads}")

    # 8. Open it. The window that replaces the debugger carries its own
    #    NAVIGATION BAR, which is the only thing that tells the two screens
    #    apart — both also carry a static text reading "Select Live Network".
    ui.expect(ui.tap_text(LIVE_NETWORK), f"{LIVE_NETWORK!r} could not be tapped")
    ui.expect(ui.on_window(LIVE_NETWORK),
              f"tapping {LIVE_NETWORK!r} did not open its window — no navigation "
              f"bar by that name. Still on the debugger: "
              f"{ui.on_max_debugger(timeout=1.0)}")
    print(f"  {LIVE_NETWORK!r} window opened")

    # 9. Only NOW look for AppLovin. It also appears on the debugger's own page
    #    under 'Completed SDK Integrations' (measured: present in the tree before
    #    this window was ever opened), so searching for the name before
    #    confirming the window could match the wrong row on the wrong screen and
    #    still look like a pass.
    ui.expect(ui._ax_rect(NETWORK), f"{NETWORK!r} is not listed on the "
                                    f"{LIVE_NETWORK!r} window")
    # Was anything ALREADY selected? MAX says the choice "will reset on the next
    # app session", and runs do not always restart the app — so a leftover
    # selection could make the checkmark assertion below pass without this tap
    # doing anything. Reported every run rather than assumed either way: if this
    # ever prints True, the assertion has stopped proving what it claims.
    was_ticked = bool(ui._ax_first("XCUIElementTypeButton", "checkmark", timeout=6.0))
    print(f"  a network was already selected before tapping: {was_ticked}")
    ui.expect(ui.tap_text(NETWORK, settle=3.0), f"{NETWORK!r} could not be tapped")

    # 10. Selecting a network ticks it. The checkmark is a BUTTON that does not
    #     exist until something is selected, so its appearance is the proof the
    #     tap registered — the row's own text is identical either way.
    ui.expect(ui._ax_first("XCUIElementTypeButton", "checkmark", timeout=8.0),
              f"tapping {NETWORK!r} did not select it — no checkmark appeared on "
              f"the {LIVE_NETWORK!r} list")
    picked = ui.shoot("ad_applovin")
    print(f"  {NETWORK} selected (checkmark shown) — see {picked}")

    # 11. No cleanup: the run ends here on purpose, so a later chunk can carry on
    #     from this screen. Step 2 unwinds it on the next run.
    print(f"PASS: device online ({net}), Dev Panel reached, MAX's Mediation "
          f"Debugger opened, and {NETWORK} selected as the live network — left "
          f"on that screen on purpose (see {picked})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
