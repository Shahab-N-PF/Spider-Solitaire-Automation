#!/usr/bin/env python3
"""Run the functional suite and print a PASS/FAIL summary.

These tests target the **Unity** build (the Obj-C build is no longer functionally
tested). They ask "does the Unity build WORK?" — a different question from
tests/compare_unity*.py, which asks whether it LOOKS like the Obj-C baseline.

Every test launches the app and walks itself to the main menu, so one failure
cannot cascade into the next — the run always reports on all of them. Exit code
is non-zero if any test failed, for CI.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, `DEVICE_UDID` exported, and
the device in **Airplane Mode** (online, cross-promo interstitials interrupt
screen transitions — see tests/README.md).

Run:  ./.venv/bin/python tests/run_all.py
      ./.venv/bin/python tests/run_all.py verifyPlay verifyGamePlay   # a subset
      SKIP_VISUAL=1 ./.venv/bin/python tests/run_all.py               # skip baselines
"""
import importlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import unity_ui  # noqa: E402
import visual  # noqa: E402

# Order: a cold start, then cheap navigation checks (if the menu is broken
# everything else is noise), then the heavier gameplay tests, and finally the
# destructive one.
#
# NOTE THE SUITE IS NOW DESTRUCTIVE: it ends by wiping local statistics. That is
# deliberate — see the resetStats entry at the bottom of TESTS.
#
# Not in the suite, on purpose:
#   verifyHelpShift — needs the device ONLINE, which the rest of the suite
#                     specifically avoids; run it deliberately.
#   verifyAds       — needs the device ONLINE by definition (it is the ad axis).
#   visitLastScore  — its Game Center legs need the device ONLINE and a
#                     signed-in Apple account. Its first half (the picker's
#                     "Last Score", the header, the period stepper) would run
#                     offline fine, but a case that is half-checked in the
#                     offline suite is worse than one run deliberately online.
#   verifyChooseLook— REPAINTS the table and LEAVES it repainted: the chosen
#                     surface and card back are saved by the app. Sitting in the
#                     middle of a suite that reads the table, it makes every
#                     later failure ask "did that break, or did the felt move
#                     under it?" — 'menu' is white text ON the felt and scores
#                     0.74-0.84 across surfaces against a 0.72 bar. Run it alone,
#                     or last, once everything else has already run.
#   verifyRelaunch  — KILLS the app mid-game by design (its premise is that the
#                     game screen comes back after a kill). Anywhere after
#                     openDebugTools that would hide the Dev Panel button
#                     verifyVictory and verifyDifficultyLevels depend on, and the
#                     only clean slot left costs more than running it alone does.
TESTS = [
    # First because it is the only test that starts from a TERMINATED app rather
    # than walking back from wherever the last one left off — so it both checks
    # the cold-start path and hands every later test a known-clean state. On a
    # fresh install it also clears the two one-per-install gates (Terms &
    # Conditions, then the ATT prompt); on a normal launch there are no pop-ups
    # and it simply confirms a cold start reaches the menu.
    "verifyFirstLaunch",        # cold start -> menu, no pop-ups left on screen
    "verifyMainMenu",           # foundation: the menu renders at all
    "verifyStatsPage",          # renders + scrolls end to end
    "verifyOptions",            # 4 named rows driven (2 toggles, 2 sliders), then reset
    "verifyHelpPage",           # opens + the body scrolls
    "verifySpiderLogo",         # About via item + logo, links, in-app FAQ + its scroll
    "verifyMoreGamesBtn",       # in-app cross-promo page + its scroll
    "verifyPlay",               # picker shows 5 levels, Easy deals
    # openDebugTools force-restarts the app (its premise is a HIDDEN button), so
    # it must come before anything that needs the unlock — and the fewer tests
    # between it and verifyVictory, the fewer chances something restarts the app
    # and hides the button again.
    "openDebugTools",           # hidden QA entry point (5 taps -> Dev Panel)
    "verifyGamePlay",           # the table actually plays (deal/undo, drawer)
    "verifyVictory",            # the win screen (reached via the QA cheat)
    # After openDebugTools for a REASON OF ITS OWN, not just ordering: this test
    # now wins every level with the Dev Panel cheat, so it needs the same unlock
    # verifyVictory does. (It re-arms itself if the button has gone, but that
    # costs a trip to About per level.)
    #
    # Also safe after verifyVictory because that test collapses the Dev Panel
    # overlay before it returns: expanded, that overlay covers the Hard/Bold/
    # Expert rows of the difficulty picker, so this test could only ever have
    # reached Easy. verifyVictory also leaves NO game in progress, which is what
    # lets this test open on Medium with no abandon prompt to answer — and since
    # it now completes every level too, no level raises one.
    "verifyDifficultyLevels",   # medium..expert deal AND win (Easy is verifyPlay's)
    # Last on purpose: this is the one test whose result depends on the build
    # (the promo strip shipped in 341/343 and is gone again in 353), so it is the
    # most likely to be red. Keeping it at the end means the summary is not led
    # by an expected failure, and a rig problem shows up before it.
    "verifyMoreGamesIcons",     # promo strip — build-dependent (341/343 yes, 353 no)
    # LAST, and destructive: it permanently wipes local statistics on the device
    # (Game Center scores are untouched). Everything that reads or depends on
    # play history has already run by this point — verifyStatsPage renders the
    # page, verifyDifficultyLevels banks four wins, and verifyMoreGamesIcons
    # needs at least one completed game to draw the promo strip. Each run
    # re-earns all of that before it gets here, so wiping at the end leaves the
    # next run's ordering intact rather than breaking it.
    "resetStats",               # reset link + both confirmations (DESTRUCTIVE)
]

# Tests that are currently EXPECTED to fail because the Unity port dropped the
# feature. They still run and still report FAIL — a known regression should stay
# visible — but the summary names them so a red run is not mistaken for a broken
# rig. Delete an entry once the port restores the feature.
#
# openDebugTools was listed here and is NOT any more: the QA entry point is
# present on Unity after all. The earlier "it opens nothing" reading came from
# aiming the tap burst at the About wordmark; the gesture lives on the spider
# emblem above it, and 5 rapid taps there reveal the Dev Panel button.
#
# verifyMoreGamesIcons is NOT a port gap at all, and is no longer expected to
# fail. The promo strip only appears once AT LEAST ONE GAME HAS BEEN COMPLETED —
# on a fresh install with stats at 0 the app does not draw it. That is why the
# test sits LAST in TESTS, after verifyVictory, which wins a game with the Dev
# Panel cheat and so satisfies the precondition. Keep that order.
#
# (An earlier note here called the empty strip a build-353 regression. That was
# wrong — it was written from a fresh-install capture with zero wins.)
KNOWN_UNITY_GAPS = {}


def preflight():
    """Fail fast with a readable message if the rig obviously isn't ready."""
    problems = []
    if not os.path.isdir(config.UNITY_ASSETS):
        problems.append(f"no Unity templates at {config.UNITY_ASSETS} — run "
                        "scripts/capture_unity_screens.py then "
                        "scripts/derive_unity_assets.py")
    else:
        absent = [n for n in REQUIRED if not unity_ui.have(n)]
        if absent:
            problems.append(
                f"missing {len(absent)} Unity template(s): {', '.join(absent)}\n"
                "      re-capture with scripts/capture_unity_screens.py, then\n"
                "      scripts/derive_unity_assets.py")
    try:
        import urllib.request
        urllib.request.urlopen(config.WDA_URL + "/status", timeout=8)
    except Exception:  # noqa: BLE001
        problems.append(f"WDA is not reachable at {config.WDA_URL} — "
                        "start it with scripts/wda.sh (device unlocked)")
    if not config.DEVICE_UDID:
        problems.append(
            "DEVICE_UDID is not set. Airtest otherwise picks the first device it "
            "sees, including WiFi-paired ones that aren't plugged in — export it "
            "to the same UDID you passed to scripts/wda.sh")
    return problems


# Every template the suite depends on. Checked up front so a missing crop is one
# clear message rather than a run that dies halfway with "control not found".
REQUIRED = [
    "menu_play", "menu_stats", "menu_options", "menu_help", "menu_about",
    "more_games", "choose_look", "menu_logo",
    "back_bar", "screen_options", "contact_us", "opt_sounds", "opt_cards",
    "opt_interface", "screen_stats", "game_center", "reset_stats", "screen_help",
    "screen_about", "about_version", "about_faq", "about_help", "about_feedback",
    "about_emblem", "dev_panel", "screen_more_games",
    # look_close only. The other Choose Look crops (look_surface_tab,
    # look_cards_tab, screen_surface, screen_cards) went with verifyChooseLook
    # when it left TESTS — this list gates the OFFLINE SUITE, and a test outside
    # it asserts its own templates. look_close STAYS because the suite itself
    # needs it: ui.on_menu() calls is_on("look_close") on every check to rule out
    # the Choose Look modal sitting over the menu, and ui.to_menu() taps it to
    # escape. Without the crop that guard silently disappears.
    "look_close",
    "dialog_no", "dialog_yes", "prompt_abandon",
    "difficulty_easy", "difficulty_medium", "difficulty_hard", "difficulty_bold",
    "difficulty_expert",
    "back_game", "in_game_menu", "tap_undo", "tap_lower", "tap_hints",
    "ingame_replay", "ingame_abandon", "ingame_options", "ingame_new",
    "ingame_help", "ingame_faq",
    # QA cheat + the victory screen it makes reachable
    "dev_complete_game", "screen_victory", "victory_ranking",
    "victory_leaderboards", "victory_achieve", "victory_help", "victory_new",
    "victory_stats", "victory_level_easy", "about_back", "stats_back",
    # the card suit pips verifyGamePlay reads to prove "Use Hearts" reached the
    # dealt cards
    "card_spade", "card_heart",
    # the two first-launch gates verifyFirstLaunch has to clear (both by image —
    # WDA can see neither)
    "tc_continue", "att_prompt", "att_allow",
]
# Deliberately NOT listed: "resume", the difficulty picker's ribbon that
# verifyGamePlay uses to carry on with a paused game instead of dealing over it.
# That is an OPTIMISATION with a working fallback — ui.resume_or_deal() deals
# when the ribbon is not there, and says so on stdout — so a missing crop should
# cost one deal, not block the whole suite in preflight. (It is also the one
# template the offline gate cannot check: the ribbon is only drawn while a game
# is PAUSED, which capture_unity_screens.py never leaves it.)
#
# Also deliberately NOT listed: last_score / screen_last_score / last_score_next
# and the gc_* Game Center crops. This list gates the OFFLINE suite, and
# visitLastScore is not in it — checking its templates here would stop a healthy
# run over crops nothing in the run touches. That test asserts its own.


def main():
    picked = [a for a in sys.argv[1:] if not a.startswith("-")]
    tests = picked or TESTS

    problems = preflight()
    if problems:
        print("preflight failed:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(2)

    results = []
    for name in tests:
        mod = importlib.import_module(f"tests.{name}")
        print(f"\n=== {name} ===")
        t0 = time.time()
        try:
            mod.run()
            results.append((name, True, time.time() - t0))
        except Exception as e:  # noqa: BLE001
            print(f"FAIL: {e}")
            results.append((name, False, time.time() - t0))

    print("\n" + "=" * 56)
    print("  functional tests (Unity build)")
    passed = sum(1 for _, ok, _ in results if ok)
    unexpected = 0
    for name, ok, dt in results:
        note = ""
        if not ok and name in KNOWN_UNITY_GAPS:
            note = "   [known Unity gap]"
        elif not ok:
            unexpected += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name:24} ({dt:5.1f}s){note}")
    print(f"  {passed}/{len(results)} passed")

    gaps = [n for n, ok, _ in results if not ok and n in KNOWN_UNITY_GAPS]
    if gaps:
        print("\n  known Unity port gaps (expected failures, not rig problems):")
        for n in gaps:
            print(f"    - {n}: {KNOWN_UNITY_GAPS[n]}")

    visual_ok = run_visual_phase()
    sys.exit(0 if (unexpected == 0 and visual_ok) else 1)


def run_visual_phase():
    """Compare captured screenshots to the Obj-C baselines.

    OFF by default now. The captures this suite produces come from the Unity
    build, and baselines/ is the Obj-C reference for the port — so a comparison
    here reports the whole Obj-C/Unity delta, which is the dedicated job of
    tests/compare_unity*.py (with per-device masks and curated thresholds this
    phase doesn't have). Set RUN_VISUAL=1 to include it anyway.
    """
    if not os.environ.get("RUN_VISUAL"):
        return True

    print("\n" + "=" * 56)
    print("  baseline comparison (exact-pixel vs baselines/ — Obj-C reference)")
    results = visual.compare_all()
    regressed = 0
    for r in results:
        mark = {"pass": "PASS", "fail": "FAIL", "no-baseline": "----"}.get(r["status"], "????")
        if r["status"] not in ("pass", "no-baseline"):
            regressed += 1
        pct = f"{r['diff_pct']:.2f}%" if r.get("diff_pct") is not None else "  -  "
        print(f"  {mark}  {r['name']:26} diff={pct}")
    if regressed:
        print(f"  {regressed} screen(s) differ from the Obj-C baseline "
              "— expected during the port; see tests/compare_unity.py")
    return True          # informational only; the port delta is not a suite failure


if __name__ == "__main__":
    main()
