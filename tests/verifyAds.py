#!/usr/bin/env python3
"""Test: put MAX in Test Mode on Pangle, then walk the leave-game interstitial. [UNITY]

*** NEEDS THE DEVICE ONLINE — and this test puts it online itself. ***

**Chunks 1-3 of a rebuild.** verifyAds is being rebuilt around the Dev Panel's
"Max Debugger" — AppLovin MAX's own mediation debugger — instead of watching
banners from the outside. Chunks 1-2: online, into the app, into the Dev Panel
whether or not it was already unlocked, then Debug, then Max Debugger, then
MAX **Test Mode** on the **Pangle** network, ALWAYS in a fresh app session:

  * Spider is relaunched first. A "Test Mode Enabled: true" reading was
    once stale (after WDA crashed under a run, it read true with Pangle
    ticked while every ad came from live networks), so it is never trusted
    from an earlier session. A fresh session that still reads true is
    switched back to live — the Enable link then sits on the live row — and
    restarted, before Test Mode is enabled again.
  * Test Mode OFF (the Ads section's "Test Mode Enabled" row reads false):
    tap the blue **Enable** link on the "Select Test Mode Network" row. MAX
    raises a **"Restart Required"** pop-up; OK it and relaunch Spider —
    killed from the foreground, so it comes back on the menu instead of
    restoring the table (Back from the table fires an interstitial). The
    relaunch RE-LOCKS the Dev Panel, so it is unlocked again the usual way
    (5 taps on About's emblem) and the debugger reopened. Test Mode must be
    on after the relaunch — FAIL if it is not.

Then **Select Test Mode Network** opens its own window; **Pangle** is ticked
there (left alone when it already is) and the debugger is closed.

THE SETUP RELAUNCHES ARE THE ONLY DELIBERATE COLD LAUNCHES. Everywhere else
this test refuses to relaunch, because a relaunch re-locks the Dev Panel; here
MAX requires it, and the Dev Panel is unlocked again straight after.

TEST MODE LASTS ONE APP SESSION. It is on for the session the restart
starts, and off again after the next relaunch (measured on 8.0.4: Pangle
ticked, relaunch, "Test Mode Enabled" read false). Until then every ad is a
Pangle test ad. The steps live in max_test_mode.py (ensure_network), which
triggerAdPoints runs at its own start too.

Chunk 3: close those overlays, reach a game (resume if one is paused,
otherwise deal Easy), wait ~30s, tap back, and close the interstitial —
landing back on the **game table**. A Pangle test ad opens no StoreKit
sheet: about 5s in, a grey double-arrow sits top right; one tap closes the ad
or skips to an end card whose dark X closes it (``close_interstitial_chain``).
Ads are only ever triggered from a test network; a relaunch after setup turns
Test Mode back on (``max_test_mode``), and an ad that closes without Pangle's
skip or X is a LIVE ad: the test re-enables Test Mode and FAILs. If
back does not show the interstitial (``log/ad_back_no_ad.png`` records what
was there), the test deals a fresh Easy game — Resume no longer fires an ad
(TA-09 was retired) — and, if that shows none either, waits ~30s on the new
table and presses Back again (TA-07). It FAILs only when all three miss.

**IT ENDS ON THE TABLE ON PURPOSE**, so a later chunk (VERIFY_ADS_CHUNK=3)
can carry on from that screen in the same session. A full re-run only unwinds
native leftovers (debugger, network window, restart pop-up) and then lets the
fresh relaunch clear everything else — it never walks off the table first,
because back() from there fires an ad before Test Mode is on.

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
    Live Network" read y=102 while off screen and "AppLovin" read y=-409. Only
    the `visible` attribute says a row is really drawn, which is why the scroll
    waits for visibility rather than presence.

NETWORK NAMES ARE AMBIGUOUS. "Pangle" also appears on the debugger's own page
under "Completed SDK Integrations", in the tree before the network window is
ever opened. So that window is confirmed FIRST — by its navigation bar — and
only then is Pangle looked for.

WHAT EARLIER WORK ESTABLISHED, kept because later chunks rebuild on it (the
banner/interstitial version of this test is in git history):
  * interstitials fire on leaving a game — 12 of 12 attempts — and render
    INSIDE the app; the foreground app stays Spider;
  * live creatives CHAIN: a video plays ~15s, then opens an App Store product
    sheet BY ITSELF with no tap, and closing that starts a further playable ad;
  * if leaving a game does NOT show an interstitial, it used to on the next
    resume or new deal; Resume no longer does. Setup absorbs a picker ad
    with ui.ad_free() so we can reach the table; the enter-after-back path
    must NOT, because that ad is the assertion. Never ui.recover() — a cold launch re-locks the
    Dev Panel.
Live creatives' "▶▶" skip glyph moved between creatives and a crop scored
0.65-0.75 on real ads but 0.656 on the plain menu, so it was never tapped.
Pangle's double-arrow never moves, which is why it is.

Captures log/ad_dev_panel.png, log/ad_max_debugger.png,
log/ad_restart_required.png (only when Test Mode was off),
log/ad_test_mode_section.png, log/ad_pangle.png, log/ad_back_on_table.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
         The device may start offline — this test brings it online.
Run:  ./.venv/bin/python tests/verifyAds.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import max_test_mode as mtm  # noqa: E402
import unity_ui as ui  # noqa: E402

NETWORK = mtm.NETWORK
TABLE_WAIT = 30.0
CLOSE_WAIT = 90.0
AD_CLOSE_WAIT = 30.0


def _reach_table():
    """Resume a paused game or deal Easy.

    Returns ``(description, ad_active)``. An interstitial during
    ``resume_or_deal`` is expected ad behavior, not a setup failure: the
    caller owns the same close sequence as an ad that appeared on Back.
    ``recover()`` is forbidden because a cold launch re-locks the Dev Panel.
    """
    try:
        return ui.resume_or_deal("easy"), False
    except AssertionError as e:
        if not (ui.lost() and ui.in_app()):
            raise
        print(f"  interstitial appeared during resume_or_deal ({e}) — "
              "expected ad behavior; closing it as chunk 3")
        return "interstitial during resume_or_deal", True


def _close_ad(where: str) -> bool:
    """Close the ad; FAIL (after re-enabling Test Mode) if it was a live one."""
    ok = ui.close_interstitial_chain(where, CLOSE_WAIT, AD_CLOSE_WAIT)
    if ui.last_ad_was_live():
        raise AssertionError(mtm.live_ad_served(where))
    return ok


def _enter_for_ad():
    """Deal a fresh Easy game. The interstitial may fire HERE.

    Resume no longer fires an interstitial (TA-09 was retired), so the paused
    game is abandoned for a new deal instead. Must not call ad_free()/recover()
    — that would swallow the ad this step is waiting for.
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

    print("  dealing a fresh Easy game — the interstitial may appear now")
    ui.expect(ui.tap("difficulty_easy", settle=2.0), "Easy could not be tapped")
    # Over a paused game, Easy raises the abandon prompt; settle_prompts()
    # answers it Yes. An ad, if it fires, stays up for wait_lost() below.
    if ui.alert_now():
        ui.settle_prompts()
    return "dealing a fresh Easy game"


def _restore_table_after_ad():
    """Restore the paused game without a cold launch after the ad closes."""
    if not ui.at_table(timeout=8.0):
        print("  ad closed to the menu/picker — restoring the paused game")
        how, ad_active = _reach_table()
        print(f"  {how}")
        if ad_active:
            _close_ad("resume_or_deal after the first ad")
            return _restore_table_after_ad()
        ui.settle_prompts()
        ui.expect(ui.at_table(timeout=8.0),
                  "restoring the paused game after the ad did not reach "
                  "the table")
    return ui.shoot("ad_back_on_table")


def _leave_table_for_ad() -> str:
    """Wait on the table, tap back, and return where the interstitial fired."""
    print(f"  waiting {TABLE_WAIT:.0f}s on the table for an interstitial to arm")
    ui.sleep(TABLE_WAIT)
    ui.expect(ui.back(), "the table's back control could not be tapped")
    # It usually fires on back. When it does not, deal a fresh game; if that
    # shows none either, a second long table visit ending in Back (TA-07) is
    # the documented trigger. A hand-off out of Spider is a different failure
    # from "still on a Spider screen".
    if ui.wait_lost(timeout=12.0):
        print("  interstitial fired on back")
        return "leaving the game"
    missed = ui.shoot("ad_back_no_ad")
    print(f"  no interstitial on back (see {missed}) — dealing a fresh game")
    where = _enter_for_ad()
    if ui.wait_lost(timeout=20.0):
        return where
    ui.expect(ui.at_table(timeout=8.0),
              f"{where} showed no interstitial and did not reach the table — "
              f"foreground app: {ui.active_app() or 'unknown'}")
    print(f"  no interstitial on the deal either — waiting {TABLE_WAIT:.0f}s "
          "on the new table and pressing Back again")
    ui.sleep(TABLE_WAIT)
    ui.expect(ui.back(), "the table's back control could not be tapped")
    ui.expect(ui.wait_lost(timeout=12.0),
              f"no interstitial on back, on {where}, or on a second Back after "
              f"{TABLE_WAIT:.0f}s on the table — still on a recognisable Spider "
              f"screen (first miss: {missed}). Foreground app: "
              f"{ui.active_app() or 'unknown'}")
    return "leaving the new game"


def run_chunk3(net):
    """Run only chunk 3 from the current Spider state.

    This is deliberately separate from ``run``: chunks 1-2 have already put
    MAX on Pangle, and rerunning them can disturb the debugger's scroll
    position. The current screen may be a leftover debugger, table, menu, or
    the expected interstitial itself.
    """
    mtm.close_overlays()
    if ui.lost(timeout=2.0):
        _close_ad("resume_or_deal")
        table = _restore_table_after_ad()
        print(f"PASS: chunk 3 closed the expected interstitial and "
              f"returned to the table (see {table})")
        return

    if not ui.at_table(timeout=2.0):
        how, ad_active = _reach_table()
        print(f"  {how}")
        if ad_active:
            _close_ad("resume_or_deal")
            table = _restore_table_after_ad()
            print(f"PASS: chunk 3 accepted the interstitial during "
                  f"resume_or_deal and returned to the table (see {table})")
            return
    ui.settle_prompts()
    ui.expect(ui.at_table(), "did not reach the game table")
    where = _leave_table_for_ad()
    _close_ad(where)
    table = _restore_table_after_ad()
    print(f"PASS: chunk 3 closed the interstitial and returned to "
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

    # 2. Unwind native leftovers from a previous run (the debugger, a network
    #    window, MAX's restart pop-up). Nothing else needs unwinding and no
    #    screen needs reaching: ensure_network() relaunches Spider first, which
    #    clears a leftover ad or table — walking off a table here would fire
    #    an ad before Test Mode is on, i.e. a LIVE ad.
    mtm.unwind_leftovers()

    # 3-10. Fresh app session -> Dev Panel -> Max Debugger -> Test Mode on
    #       (enabling it relaunches Spider and re-unlocks the panel) -> Pangle
    #       ticked -> Back, Done, collapse the panel.
    mtm.ensure_network(NETWORK)

    # ── chunk 3 ──────────────────────────────────────────────────
    # The debugger was opened from About: walk to the menu and deal/resume.
    ui.expect(ui.to_menu(),
              "could not walk back to the main menu from About after "
              "closing the debugger")
    print("  debugger closed, back on the main menu")
    how, ad_active = _reach_table()
    print(f"  {how}")
    ui.settle_prompts()
    if ad_active:
        _close_ad("resume_or_deal")
        table = _restore_table_after_ad()
        print(f"PASS: device online ({net}), MAX Test Mode on {NETWORK}, and "
              f"the expected resume_or_deal interstitial was closed — left on "
              f"the table (see {table})")
        return
    ui.expect(ui.at_table(), "did not reach the game table")

    # 11-12. Wait for MAX to prefetch, leave, close the interstitial.
    where = _leave_table_for_ad()
    _close_ad(where)
    table = _restore_table_after_ad()

    print(f"PASS: device online ({net}), MAX Test Mode on {NETWORK}, "
          f"leave-game interstitial closed, back on the table — left there on "
          f"purpose (see {table})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
