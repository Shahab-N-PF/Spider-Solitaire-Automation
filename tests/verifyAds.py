#!/usr/bin/env python3
"""Test: pin AppLovin in MAX's debugger, then walk the leave-game interstitial. [UNITY]

*** NEEDS THE DEVICE ONLINE — and this test puts it online itself. ***

**Chunks 1-3 of a rebuild.** verifyAds is being rebuilt around the Dev Panel's
"Max Debugger" — AppLovin MAX's own mediation debugger — instead of watching
banners from the outside. Chunks 1-2: online, into the app, into the Dev Panel
whether or not it was already unlocked, into the debugger, down to its **Ads**
section, into **Select Live Network** (or **Live Network** when one is already
selected), and **AppLovin** selected as the live network. Chunk 3: close those
overlays, reach a game (resume if one is paused,
otherwise deal Easy), wait ~30s, tap back, and walk the interstitial chain —
StoreKit product-sheet X, then the ad's own X — landing back on the **game
table**. If back does not show the interstitial, it fires on the **next**
resume of the paused game or on dealing a new one — that second enter is
the fallback, not a failure.

**IT ENDS ON THE TABLE ON PURPOSE**, so a later chunk can carry on from that
screen. A re-run therefore starts on the table (or behind leftover debugger
overlays if an earlier run died in chunks 1-2). Step 2 unwinds whichever of
those it finds. It does NOT call launch_to_menu() from the table: back() from
there fires another interstitial, and to_menu() answers lost() with recover(),
which COLD-LAUNCHES, RE-LOCKS the Dev Panel, and drops the AppLovin selection.

Still NOT in run_all.py's TESTS: the suite runs offline on purpose (ads
interrupt screen transitions and make navigation flaky), and this needs the
network.

WHY THE DEBUGGER IS READ, NOT MATCHED. It is native UIKit drawn over the Unity
view — the foreground app stays com.fingerarts.Spider — so unlike the game it
publishes a real accessibility tree. Its title is the anchor. Measured on build
363 it lists Bundle ID com.fingerarts.Spider, App Version 8.0.0, OS iOS 26.5,
Account 9441, Mediation Provider max, MAX SDK 13.6.2, Plugin Max-Unity-8.6.3,
Unity 6000.0.73f1, then every integrated ad network.

Three things measured here that shape the debugger steps:
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

THE INTERSTITIAL CHAIN (chunk 3) is also read, not guessed. The video plays
inside the app (~15s), then opens an in-app StoreKit product sheet BY ITSELF.
The sheet's X is a native Close button (fallback: ad_store_close if a crop
exists). Closing it reveals the ad's own X. The skip glyph is deliberately
NOT tapped: its position moves between creatives and a crop scores 0.65-0.75
on real ads but 0.656 on the plain main menu. After the second X the table
comes back — that is the assertion, not "the menu is reachable".

WHAT EARLIER WORK ESTABLISHED, kept because later chunks rebuild on it (the
banner/interstitial version of this test is in git history):
  * interstitials fire on leaving a game — 12 of 12 attempts — and render
    INSIDE the app; the foreground app stays Spider;
  * they CHAIN: a video plays ~15s, then opens an App Store product sheet BY
    ITSELF with no tap (confirmed with screenshot-only sampling, 40 frames, no
    touch events), and closing that starts a further playable ad;
  * watched for a full 5 minutes without pinning a network, only ONE closable
    control ever appeared (the sheet's X, at t+27s) and Spider's own UI never
    came back on its own — pinning AppLovin first is what makes the second X
    show;
  * if leaving a game does NOT show an interstitial, it will on the next
    resume or new deal. Setup absorbs a picker ad with ui.ad_free() so we
    can reach the table; the enter-after-back path must NOT, because that
    ad is the assertion. Never ui.recover() — a cold launch re-locks the
    Dev Panel and drops AppLovin.
ui.ad_free() / ui.lost() / ui.dismiss_ad() / ui.tap_store_close() /
ui.tap_ad_close() are the helpers this uses. ui.recover() is not.

Captures log/ad_dev_panel.png, log/ad_max_debugger.png, log/ad_ads_section.png,
log/ad_applovin.png, log/ad_interstitial.png, log/ad_store_closed.png,
log/ad_back_on_table.png.

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
LIVE_NETWORK_SELECTED = "Live Network"
NETWORK = "AppLovin"
SWIPES = 8
TABLE_WAIT = 30.0
STORE_WAIT = 90.0
AD_CLOSE_WAIT = 30.0


def _visible_live_network_row():
    """Visible debugger row label for live-network selection, or None."""
    for label in (LIVE_NETWORK, LIVE_NETWORK_SELECTED):
        if ui._ax_rect(label):
            return label
    return None


def _scroll_to_live_network(max_swipes: int):
    """Scroll until either unselected or selected live-network row is visible."""
    for _ in range(max_swipes):
        label = _visible_live_network_row()
        if label:
            return label
        ui.scroll(down=True)
    return _visible_live_network_row()


def _live_network_is(network: str, row_label: str) -> bool:
    """True when the debugger's visible Live Network row shows ``network``."""
    live = ui._ax_rect(row_label)
    selected = ui._ax_rect(network)
    if not live or not selected:
        return False
    live_y = live["y"] + live["height"] / 2
    selected_y = selected["y"] + selected["height"] / 2
    return abs(live_y - selected_y) <= max(
        live["height"], selected["height"], 24)


def _reach_table():
    """Resume a paused game or deal Easy.

    Returns ``(description, ad_active)``. An interstitial during
    ``resume_or_deal`` is expected ad behavior, not a setup failure: the
    caller owns the same StoreKit-X -> ad-X close sequence as an ad that
    appeared on Back. ``recover()`` is forbidden because a cold launch
    re-locks the Dev Panel and drops the AppLovin selection.
    """
    try:
        return ui.resume_or_deal("easy"), False
    except AssertionError as e:
        if not (ui.lost() and ui.in_app()):
            raise
        print(f"  interstitial appeared during resume_or_deal ({e}) — "
              "expected ad behavior; closing it as chunk 3")
        return "interstitial during resume_or_deal", True


def _enter_for_ad():
    """Resume the paused game, or deal Easy. The interstitial is expected HERE.

    After back() with no ad, the game is paused. The next enter is when the
    interstitial actually loads. Must not call ad_free()/recover() — that
    would swallow the ad this step is waiting for.
    """
    if ui.alert_now():
        ui.settle_prompts()

    # A successful back() call only proves that WDA sent the tap; the game can
    # remain on the table. Retry the table's Back control instead of returning
    # without initiating the resume/deal action this helper promises.
    if ui.at_table(timeout=1.5):
        print("  first back left the table visible — retrying Back before "
              "resume/deal")
        ui.expect(ui.back(),
                  "the retry Back control could not be tapped")
        if ui.wait_lost(timeout=3.0):
            return "retrying Back from the game table"

    if ui.at_screen("difficulty", timeout=2.0):
        print("  on the difficulty picker after back")
    elif ui.on_menu(timeout=2.0):
        ui.expect(ui.open_picker(), "Play did not open the difficulty picker")
    else:
        ui.expect(ui.to_menu(),
                  "could not reach the menu to resume/deal after back showed no ad")
        ui.expect(ui.open_picker(), "Play did not open the difficulty picker")

    if ui.have("resume") and ui.is_on("resume"):
        print("  resuming the paused game — interstitial should appear now")
        ui.expect(ui.tap("resume", settle=2.0), "the Resume ribbon could not be tapped")
        return "resuming the paused game"
    print("  no Resume ribbon — dealing Easy, interstitial should appear now")
    ui.expect(ui.tap("difficulty_easy", settle=2.0), "Easy could not be tapped")
    return "dealing a fresh Easy game"


def _close_debugger_overlays():
    """Leave chunk 2's native overlays without restarting Spider."""
    if ui.on_window(LIVE_NETWORK, timeout=2.0):
        ui.expect(ui._tap_named("XCUIElementTypeButton", "BackButton"),
                  f"could not back out of the {LIVE_NETWORK!r} window")
        ui.sleep(2)
    if ui.on_max_debugger(timeout=2.0):
        ui.expect(ui.close_max_debugger(),
                  "could not close the debugger; its 'Done' button is top-left "
                  "('Share' sits beside it)")
    if ui.is_on("dev_complete_game"):
        ui.expect(ui.close_dev_panel(),
                  "could not collapse the Dev Panel overlay")


def _restore_table_after_ad():
    """Restore the paused game without a cold launch after the ad closes."""
    if not ui.at_table(timeout=8.0):
        print("  ad closed to the menu/picker — restoring the paused game")
        how, ad_active = _reach_table()
        print(f"  {how}")
        if ad_active:
            ui.close_interstitial_chain(
                "resume_or_deal after the first ad", STORE_WAIT, AD_CLOSE_WAIT)
            return _restore_table_after_ad()
        ui.settle_prompts()
        ui.expect(ui.at_table(timeout=8.0),
                  "restoring the paused game after the ad did not reach "
                  "the table")
    return ui.shoot("ad_back_on_table")


def run_chunk3(net):
    """Run only chunk 3 from the current Spider state.

    This is deliberately separate from ``run``: chunks 1-2 have already
    selected AppLovin, and rerunning them can disturb the debugger's scroll
    position. The current screen may be a leftover debugger, table, menu, or
    the expected interstitial itself.
    """
    _close_debugger_overlays()
    if ui.lost(timeout=2.0):
        ui.close_interstitial_chain("resume_or_deal",
                                    STORE_WAIT, AD_CLOSE_WAIT)
        table = _restore_table_after_ad()
        print(f"PASS: chunk 3 closed the expected interstitial chain and "
              f"returned to the table (see {table})")
        return

    ad_active = False
    if ui.at_table(timeout=2.0):
        ui.settle_prompts()
        print(f"  current state is the table; waiting {TABLE_WAIT:.0f}s")
        ui.sleep(TABLE_WAIT)
        ui.expect(ui.back(), "the table's back control could not be tapped")
        where = "leaving the game"
        if not ui.wait_lost(timeout=12.0):
            print("  no interstitial on back — trying the next resume/deal")
            where = _enter_for_ad()
            ui.expect(ui.wait_lost(timeout=20.0),
                      f"{where} did not open an interstitial either")
    else:
        how, ad_active = _reach_table()
        print(f"  {how}")
        if ad_active:
            ui.close_interstitial_chain("resume_or_deal",
                                        STORE_WAIT, AD_CLOSE_WAIT)
            table = _restore_table_after_ad()
            print(f"PASS: chunk 3 accepted the interstitial during "
                  f"resume_or_deal and returned to the table (see {table})")
            return
        ui.settle_prompts()
        ui.expect(ui.at_table(), "did not reach the game table")
        print(f"  waiting {TABLE_WAIT:.0f}s on the table")
        ui.sleep(TABLE_WAIT)
        ui.expect(ui.back(), "the table's back control could not be tapped")
        where = "leaving the game"
        if not ui.wait_lost(timeout=12.0):
            print("  no interstitial on back — trying the next resume/deal")
            where = _enter_for_ad()
            ui.expect(ui.wait_lost(timeout=20.0),
                      f"{where} did not open an interstitial either")

    ui.close_interstitial_chain(where, STORE_WAIT, AD_CLOSE_WAIT)
    table = _restore_table_after_ad()
    print(f"PASS: chunk 3 closed the interstitial chain and returned to "
          f"the table (see {table})")


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

    # Attach Airtest without restarting. lost()/at_table() need a device, and
    # on the first call in a fresh process nothing has attached one yet —
    # that is airtest's "No devices added."
    ui.launch()

    if os.environ.get("VERIFY_ADS_CHUNK") == "3":
        run_chunk3(net)
        return

    # 2. Unwind leftovers from a previous run. A finished run now ends on the
    #    GAME TABLE; a run that died in chunks 1-2 may still have the debugger
    #    up. Never launch_to_menu() from the table — back() fires an
    #    interstitial and to_menu() answers lost() with recover(), which
    #    cold-launches and re-locks the Dev Panel.
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
    if ui.lost(timeout=2.0):
        print("  a previous run left an ad up — clearing it without relaunching")
        ui.expect(ui.ad_free(),
                  "a leftover interstitial would not close; refusing to "
                  "cold-launch because that re-locks the Dev Panel and drops "
                  f"the {NETWORK} selection")
    on_table = ui.at_table(timeout=2.0)
    ad_active = False
    if on_table:
        print("  a previous run left a game on the table — opening the Dev "
              "Panel from here rather than walking to the menu (back from the "
              "table fires another interstitial)")
    else:
        ui.expect(ui.launch_to_menu(), "could not reach the main menu")

    # 3. Into the Dev Panel. ONE call covers both cases the requirement names:
    #    already unlocked (button on this screen, including the table) -> just
    #    expand it; not unlocked -> go to About, fire the 5 rapid taps on the
    #    spider emblem, then expand. Both are idempotent.
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

    # 5-6. Open the debugger. Chunk 2 continues from here.
    ui.expect(ui.tap(BUTTON, settle=4.0), "the 'Max Debugger' button could not be tapped")
    ui.expect(ui.on_max_debugger(),
              f"tapping 'Max Debugger' did not open MAX's mediation debugger "
              f"— {ui.MAX_DEBUGGER!r} is not in the accessibility tree. The "
              f"foreground app is {ui.active_app() or 'unknown'}.")
    shot = ui.shoot("ad_max_debugger")
    print(f"  MAX Mediation Debugger is open — see {shot}")

    # ── chunk 2 ──────────────────────────────────────────────────
    # 7. The Ads section is below the fold. Its row says "Select Live Network"
    #    when empty and changes to "Live Network" once a choice is persisted.
    #    Scroll until EITHER label is VISIBLE, not merely present in the tree.
    row_label = _scroll_to_live_network(max_swipes=SWIPES)
    if not row_label:
        # The search only goes DOWN. A leftover scroll position (or a reopened
        # debugger that remembered one) puts Ads ABOVE the viewport, and more
        # down-swipes move further away. Close and reopen from the top.
        print("  Ads section not in view — reopening the debugger from the top")
        ui.expect(ui.close_max_debugger(),
                  "could not close the debugger to reset its scroll")
        ui.expect(ui.is_on(BUTTON) or ui.open_dev_panel(),
                  "Dev Panel is gone after closing the debugger")
        ui.expect(ui.tap(BUTTON, settle=4.0),
                  "could not reopen Max Debugger after a failed scroll")
        ui.expect(ui.on_max_debugger(),
                  "reopening Max Debugger did not bring it back")
        row_label = _scroll_to_live_network(max_swipes=SWIPES)
    ui.expect(row_label,
              f"never brought {LIVE_NETWORK!r} or "
              f"{LIVE_NETWORK_SELECTED!r} into view in {SWIPES} swipes "
              f"(and a reopen-from-the-top did not help). It lives in the "
              f"debugger's 'Ads' section — if the row is in the tree but never "
              f"becomes visible, the list did not scroll.")
    ads = ui.shoot("ad_ads_section")
    print(f"  scrolled to the Ads section; found {row_label!r} — see {ads}")

    already_selected = _live_network_is(NETWORK, row_label)
    print(f"  {NETWORK} already shown on the Live Network row: "
          f"{already_selected}")

    # 8. Open it. The window that replaces the debugger carries its own
    #    NAVIGATION BAR, which is the only thing that tells the two screens
    #    apart — both also carry a static text reading "Select Live Network".
    ui.expect(ui.tap_text(row_label), f"{row_label!r} could not be tapped")
    ui.expect(ui.on_window(LIVE_NETWORK),
              f"tapping {row_label!r} did not open the {LIVE_NETWORK!r} "
              f"window — no navigation "
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
    was_ticked = already_selected or bool(
        ui._ax_first("XCUIElementTypeButton", "checkmark", timeout=6.0))
    print(f"  a network was already selected before tapping: {was_ticked}")
    if not already_selected:
        ui.expect(ui.tap_text(NETWORK, settle=3.0),
                  f"{NETWORK!r} could not be tapped")
    else:
        print(f"  keeping the existing {NETWORK} selection")

    # 10. Selecting a network ticks it. The checkmark is a BUTTON that does not
    #     exist until something is selected, so its appearance is the proof the
    #     tap registered — the row's own text is identical either way.
    ui.expect(ui._ax_first("XCUIElementTypeButton", "checkmark", timeout=8.0),
              f"tapping {NETWORK!r} did not select it — no checkmark appeared on "
              f"the {LIVE_NETWORK!r} list")
    picked = ui.shoot("ad_applovin")
    print(f"  {NETWORK} selected (checkmark shown) — see {picked}")

    # ── chunk 3 ──────────────────────────────────────────────────
    # 11. Close the debugger overlays and walk to the menu WITHOUT
    #     launch_to_menu() — from this overlay that cold-launches.
    ui.expect(ui._tap_named("XCUIElementTypeButton", "BackButton"),
              f"could not back out of the {LIVE_NETWORK!r} window")
    ui.sleep(2)
    ui.expect(ui.close_max_debugger(),
              "could not close the debugger; its 'Done' button is top-left "
              "('Share' sits beside it)")
    ui.expect(ui.close_dev_panel(),
              "could not collapse the Dev Panel overlay — it covers the menu "
              "labels, so on_menu()/open_picker() cannot see them")
    # A re-run that opened the debugger from the table is already there —
    # to_menu() would tap back and fire the interstitial before the 30s wait.
    # A first run opened it from About, so walk to the menu and deal/resume.
    if ui.at_table(timeout=2.0):
        print("  debugger closed, already on the table")
    else:
        ui.expect(ui.to_menu(),
                  "could not walk back to the main menu from About after "
                  "closing the debugger")
        print("  debugger closed, back on the main menu")
        how, ad_active = _reach_table()
        print(f"  {how}")
    ui.settle_prompts()
    if ad_active:
        ui.close_interstitial_chain("resume_or_deal",
                                    STORE_WAIT, AD_CLOSE_WAIT)
        table = _restore_table_after_ad()
        print(f"PASS: device online ({net}), {NETWORK} selected as the live "
              f"network, and the expected resume_or_deal interstitial was "
              f"closed — left on the table (see {table})")
        return
    ui.expect(ui.at_table(), "did not reach the game table")

    # 13. Wait for MAX to prefetch, then leave. The interstitial fires on
    #     leaving a game, not on arriving.
    print(f"  waiting {TABLE_WAIT:.0f}s on the table for an interstitial to arm")
    ui.sleep(TABLE_WAIT)
    ui.expect(ui.back(), "the table's back control could not be tapped")

    # 14. Interstitial is inside the app. It often fires on back; when it
    #     does not, it fires on the next resume or new deal. A hand-off out
    #     of Spider is a different failure from "still on a Spider screen".
    where = "leaving the game"
    if ui.wait_lost(timeout=12.0):
        print("  interstitial fired on back")
    else:
        print("  no interstitial on back — it fires on the next resume/deal")
        where = _enter_for_ad()
        ui.expect(ui.wait_lost(timeout=20.0),
                  f"{where} did not open an interstitial either — still on a "
                  "recognisable Spider screen. Foreground app: "
                  f"{ui.active_app() or 'unknown'}")
    ui.close_interstitial_chain(where, STORE_WAIT, AD_CLOSE_WAIT)
    table = _restore_table_after_ad()

    print(f"PASS: device online ({net}), {NETWORK} selected as the live "
          f"network, leave-game interstitial closed (store X then ad X), "
          f"back on the table — left there on purpose (see {table})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
