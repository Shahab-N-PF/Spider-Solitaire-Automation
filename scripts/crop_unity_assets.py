#!/usr/bin/env python3
"""Crop the Unity build's UI anchors out of its own screenshots.

Why this exists: the inherited `assets/` templates were cropped from the
OBJ-C renderer, so they don't match the Unity build — which is why the
pixel-fidelity tools (tests/compare_unity*.py) drive Unity by blind coordinates.
For FUNCTIONAL testing we want the opposite: templates cropped from UNITY's own
rendering, so the suite can *find* a control (and assert it exists) instead of
tapping a hardcoded point and hoping.

Source frames are the committed Unity captures (log/ip14_unity_343/*.png,
iPhone 14 Pro Max, 1290x2796). Output goes to iphone14/assets_unity/.

Boxes are (x1, y1, x2, y2) in the source frame's pixel space. Keep them tight
around the glyphs but off the surrounding texture — the felt background is
subtly noisy and animated, so extra margin costs match confidence.

Run:  ./.venv/bin/python scripts/crop_unity_assets.py [--check]
        --check  re-verify existing crops instead of rewriting them
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "log", "ip14_unity_343")
OUT = os.path.join(ROOT, "iphone14", "assets_unity")

# name -> (source capture, (x1, y1, x2, y2))
CROPS = {
    # ── main menu ─────────────────────────────────────────────────
    "menu_play":        ("MainMenu.png", (935, 1410, 1120, 1520)),
    "menu_stats":       ("MainMenu.png", (860, 1620, 1055, 1715)),
    "menu_options":     ("MainMenu.png", (820, 1818, 1080, 1908)),
    "menu_help":        ("MainMenu.png", (835, 2014, 985, 2104)),
    "menu_about":       ("MainMenu.png", (872, 2202, 1080, 2292)),
    "more_games":       ("MainMenu.png", (200, 1838, 375, 1942)),
    "choose_look":      ("MainMenu.png", (200, 2024, 382, 2128)),
    "menu_logo":        ("MainMenu.png", (330, 690, 910, 875)),

    # ── difficulty picker (Play) ──────────────────────────────────
    "difficulty_easy":    ("DifficultyLevels.png", (935, 1406, 1122, 1500)),
    "difficulty_medium":  ("DifficultyLevels.png", (870, 1560, 1130, 1654)),
    "difficulty_hard":    ("DifficultyLevels.png", (826, 1735, 1000, 1822)),
    "difficulty_bold":    ("DifficultyLevels.png", (817, 1884, 982, 1973)),
    "difficulty_expert":  ("DifficultyLevels.png", (834, 2049, 1078, 2143)),
    # "resume" — the picker's red Resume ribbon — is deliberately NOT cut here.
    # It is drawn only while a game is PAUSED, and capture_unity_screens.py
    # walks a clean app, so DifficultyLevels.png never contains it. The
    # committed crop came from an iPhone 11 picker captured with a game left in
    # progress: log/picker_paused.png, box (520, 1428) - (720, 1518). To re-cut
    # it for a new build, leave a game part-played, open Play, screenshot, and
    # crop the ribbon.

    # ── game table ────────────────────────────────────────────────
    "back_game":     ("Play.png", (58, 244, 230, 305)),
    "ingame_bar_new": ("Play.png", (586, 244, 704, 301)),
    "in_game_menu":  ("Play.png", (1078, 244, 1235, 301)),
    "tap_undo":      ("Play.png", (104, 2147, 340, 2199)),
    "tap_lower":     ("Play.png", (529, 2147, 762, 2199)),
    "tap_hints":     ("Play.png", (942, 2144, 1196, 2196)),
    "tap_to_start":  ("Play.png", (353, 2007, 938, 2070)),

    # ── in-game menu bar ──────────────────────────────────────────
    "ingame_replay":  ("InGameMenu.png", (351, 2014, 550, 2087)),
    "ingame_abandon": ("InGameMenu.png", (803, 2014, 1060, 2087)),
    "ingame_options": ("InGameMenu.png", (349, 2158, 550, 2234)),
    "ingame_new":     ("InGameMenu.png", (868, 2158, 1000, 2234)),
    "ingame_help":    ("InGameMenu.png", (383, 2303, 515, 2378)),
    "ingame_faq":     ("InGameMenu.png", (866, 2303, 1004, 2378)),

    # ── options screen ────────────────────────────────────────────
    "back_bar":       ("OptionsPage.png", (58, 202, 236, 268)),
    "screen_options": ("OptionsPage.png", (481, 191, 813, 273)),
    "contact_us":     ("OptionsPage.png", (973, 202, 1232, 268)),
    "opt_sounds":     ("OptionsPage.png", (484, 361, 721, 422)),
    "opt_cards":      ("OptionsPage.png", (508, 1596, 700, 1657)),
    "opt_interface":  ("OptionsPage.png", (455, 2478, 755, 2539)),

    # ── statistics screen ─────────────────────────────────────────
    "screen_stats":  ("StatsPage.png", (435, 198, 855, 282)),
    "game_center":   ("StatsPage.png", (973, 191, 1144, 298)),
    "reset_stats":   ("StatsResetBtn.png", (428, 2573, 878, 2639)),

    # ── help screen ───────────────────────────────────────────────
    "screen_help":   ("HelpPage.png", (428, 750, 855, 818)),
    "help_rules":    ("HelpPage.png", (545, 1490, 740, 1562)),

    # ── about screen ──────────────────────────────────────────────
    "screen_about":   ("SpiderAboutPage.png", (202, 1382, 1088, 1438)),
    "about_version":  ("SpiderAboutPage.png", (452, 1258, 672, 1324)),
    "about_faq":      ("SpiderAboutPage.png", (230, 2067, 1064, 2130)),
    "about_help":     ("SpiderAboutPage.png", (575, 1809, 715, 1871)),
    "about_adfree":   ("SpiderAboutPage.png", (418, 1937, 873, 1999)),
    "about_feedback": ("SpiderAboutPage.png", (386, 2326, 902, 2388)),

    # ── more games (cross-promo) ──────────────────────────────────
    "screen_more_games": ("MoreGames.png", (862, 184, 1263, 298)),
    "back_promo":        ("MoreGames.png", (44, 191, 222, 257)),

    # ── choose look modal ─────────────────────────────────────────
    "look_surface_tab": ("choose_look_surface.png", (198, 750, 417, 818)),
    "look_cards_tab":   ("choose_look_surface.png", (705, 750, 872, 818)),
    "look_close":       ("choose_look_surface.png", (1074, 771, 1190, 885)),
    "screen_surface":   ("choose_look_surface.png", (277, 1563, 720, 1626)),
    "screen_cards":     ("choose_look_cards.png", (501, 1568, 1025, 1633)),

    # ── victory / results screen ──────────────────────────────────
    "screen_victory":   ("VictoryScreen1.png", (240, 1787, 561, 1847)),
    "victory_achieve":  ("VictoryScreen1.png", (725, 1787, 1070, 1847)),
    "victory_new":      ("VictoryScreen1.png", (585, 2310, 715, 2380)),
    "victory_stats":    ("VictoryScreen1.png", (955, 2310, 1090, 2380)),
}


# ── iPhone 11 (828x1792) hand crops ───────────────────────────────
# Most iPhone 11 templates are derived automatically from the iPhone 14 set
# (scripts/derive_unity_assets.py). These are the ones that can't be: elements
# with no iPhone 14 counterpart captured — chiefly the two look-alike Yes/No
# confirmations, which need their TEXT to be told apart because the abandon
# prompt must be answered Yes and the rules prompt No.
CROPS_IP11 = {
    "dialog_no":       ("AbandonPrompt.png", (130, 938, 404, 1018)),
    "dialog_yes":      ("AbandonPrompt.png", (424, 938, 700, 1018)),
    "prompt_abandon":  ("AbandonPrompt.png", (150, 802, 676, 892)),
    # App Tracking Transparency, the first-launch gate. Unlike everything else
    # here this one CANNOT be re-captured on demand: iOS shows it once per
    # install, so its source is a screenshot kept from a fresh install
    # (log/ip11_probe.png at the time of cutting). It is also the one prompt
    # image matching is required for — it is presented out of process, so WDA's
    # /alert/* endpoints 404 on it while it is on screen (see helpers.py).
    # The anchor is Apple's own ATT artwork, which is identical in every app.
    "att_prompt":      ("ATTPrompt.png", (146, 586, 300, 732)),
    "att_deny":        ("ATTPrompt.png", (240, 1055, 590, 1112)),
    # "Allow" — the button clear_overlays() actually presses. The app wants
    # tracking GRANTED before it lets a first launch through; answering "Ask App
    # Not to Track" (att_deny, kept for reference) does not clear the gate.
    "att_allow":       ("ATTPrompt.png", (367, 1185, 461, 1221)),
    # The OTHER first-launch gate: "To use Spider you must agree to our Terms &
    # Conditions...", with a single "Continue". It has to be matched as an image
    # because WDA CANNOT SEE IT — measured on build 363 with a live session while
    # it was on screen, /alert/text returned "" and /alert/buttons []. It is drawn
    # by the app, not presented as a UIAlertController.
    #
    # Cut tight to the blue glyphs: the card is translucent mint over the menu's
    # green felt, so a looser crop would bake the menu in behind it — the same
    # trap the iOS alert templates fell into.
    "tc_continue":     ("TermsGate.png", (341, 1064, 486, 1100)),
    # The two underlined links on that same card. verifyFirstLaunch writes its
    # live bootstrap frame at log/first_launch_terms_gate.png before Continue
    # consumes the card, so these use ../ to reach it from this profile's
    # log/unity_screens source directory.
    "tc_terms_link":   ("../first_launch_terms_gate.png",
                        (303, 769, 626, 812)),
    "tc_privacy_link": ("../first_launch_terms_gate.png",
                        (333, 864, 563, 907)),
    # Unique destination headings. Keeping these distinct is what makes a
    # swapped pair of links fail instead of merely proving that both open a
    # peoplefun.com page.
    "tc_terms_page":   ("../first_launch_terms_page.png",
                        (235, 914, 594, 978)),
    "tc_privacy_page": ("../first_launch_privacy_page.png",
                        (250, 785, 580, 850)),
    # The Spider logo on the ABOUT screen (smaller than the menu's, so it needs
    # its own crop — template matching is scale-sensitive).
    "about_logo":      ("SpiderAboutPage.png", (303, 398, 524, 512)),
    # The spider EMBLEM above that wordmark, cropped separately because it is the
    # only part of the logo that takes the hidden QA gesture: 5 rapid taps on the
    # emblem reveal the Dev Panel button, while the same burst on the wordmark
    # 50 px below changes nothing. See tests/openDebugTools.py.
    "about_emblem":    ("SpiderAboutPage.png", (336, 276, 492, 406)),
    # The Dev Panel button that gesture reveals, bottom-right. Its source capture
    # is the ONLY one here that isn't a plain screen shot — it has to be taken
    # after the gesture (tests/openDebugTools.py writes log/debug_tools.png; copy
    # one in as SpiderAboutDevPanel.png to re-cut this crop).
    "dev_panel":       ("SpiderAboutDevPanel.png", (640, 1550, 824, 1606)),
    # Entries inside the panel that button opens. "Complete Game" is the QA
    # synthetic win — the Unity equivalent of the Obj-C build's cheat — which is
    # what makes the victory screens reachable without playing a game out.
    # Source: log/unity_screens/SpiderAboutDevPanelOpen.png (About + panel open).
    "dev_complete_game": ("SpiderAboutDevPanelOpen.png", (592, 1234, 824, 1280)),
    # "Max Debugger" — the row directly BELOW Complete Game. The panel's rows
    # are 64 px apart, and its buttons are clipped by the right screen edge, so
    # this stops at the same x as its neighbour rather than chasing text that
    # is not drawn. Source: log/unity_screens/SpiderAboutDevPanelOpen.png.
    "dev_max_debugger": ("SpiderAboutDevPanelOpen.png", (592, 1298, 824, 1344)),
    # The victory screen, now reachable via that cheat. Anchored on the
    # "current / rank / best" header rather than the won/abandoned counters or the
    # score block, which change with every win. Kept left of x=587 so the Dev
    # Panel overlay (which is still up when the win fires) cannot cover it.
    # The victory screen, reachable via that cheat (source captured with the panel
    # closed, so the right-hand column is clear). Anchored on the
    # "current / rank / best" header rather than the won/abandoned counters or the
    # score block, which change with every win.
    "screen_victory":  ("VictoryClean.png", (172, 742, 560, 788)),
    "victory_ranking": ("VictoryClean.png", (352, 583, 478, 612)),
    "victory_leaderboards": ("VictoryClean.png", (159, 1138, 358, 1178)),
    "victory_achieve": ("VictoryClean.png", (470, 1138, 684, 1178)),
    # The footer names the level that was just won — the one element on this
    # screen that ties it back to the game actually played.
    "victory_level_easy": ("VictoryClean.png", (343, 1373, 485, 1404)),
    # The three red action buttons. Distinct art from the in-game drawer's
    # help/new items, so they need their own crops.
    "victory_help":    ("VictoryClean.png", (120, 1478, 240, 1528)),
    "victory_new":     ("VictoryClean.png", (358, 1478, 478, 1528)),
    "victory_stats":   ("VictoryClean.png", (592, 1478, 716, 1528)),
    # A THIRD dialog, unlike the two Yes/No ones: a "Did you know?" tip that pops
    # over the game table with OK / Show Me. "Show Me" navigates away to Options,
    # so the only safe answer is OK. It blocks taps until answered — it is what
    # swallowed the first attempt at the Complete Game cheat.
    # No "prompt_tip"/"tip_ok" here on purpose. That dialog is drawn by the app,
    # is translucent, and comes in one- and two-button forms; it is found by
    # shape instead — see unity_ui.card_dialog().
    # The in-game top bar's "menu" word, re-cut TIGHT to the glyphs. The derived
    # crop carried a wide margin of felt, and felt is the worst thing to include:
    # it changes with the Choose Look surface and with whatever cards sit behind
    # it. That version scored 0.737-0.840 on a real iPhone 16 Pro table while
    # reaching 0.744 on the Stats page — no threshold could separate them
    # (-0.007). Trimming to the glyphs (text density 0.20 -> 0.35) gives a worst
    # true match of 0.754 against a worst non-table 0.660: +0.095 of daylight.
    "in_game_menu":    ("InGameMenu.png", (695, 148, 791, 170)),
    # The Statistics header's "Game Center" caption. Cut here rather than derived
    # from the iPhone 14 set (which is where it used to come from) because build
    # 363 changed this header and the ip14 reference is still build 343. The
    # caption shrank and slid toward the screen edge — measured on the iPhone 11,
    # 828 px wide:
    #
    #   Obj-C baseline   x 635-728
    #   Unity 353        x 629-731,  59 px tall
    #   Unity 363        x 666-742,  44 px tall
    #
    # An INTENDED change, per the port owner, so the template follows it. Note
    # what that costs: the functional suite locates by sight, so re-cutting makes
    # verifyStatsPage pass again and simultaneously makes this drift invisible
    # here — it is the pixel-fidelity reports (compare_unity*.py) that must carry
    # the finding. Text only, no Game Center icon: the icon is Apple's artwork,
    # sits ~18 px further right, and can change with iOS rather than with Spider.
    #
    # Consequence, so nobody re-investigates it: scripts/verify_unity_scaling.py
    # now reports game_center MISSED on the iPhone 14 and iPhone 16 profiles.
    # That is a BUILD mismatch, not a scaling failure — those saved captures are
    # pre-363 (ip14 is build 343) and render the old, larger caption. Measured
    # both ways: the old template scores 0.975 / 0.880 on those captures and
    # 0.471 on a 363 iPhone 11 capture; this one scores 1.000 on 363 and ~0.47 on
    # them. One shared crop cannot cover both renderings, so it tracks the build
    # under test. Re-capture those devices on 363 to clear the MISSED.
    "game_center":     ("StatsPage.png", (663, 110, 746, 161)),
    # The ABOUT screen's back control, re-cut for build 363 — which shrank it and
    # slid it toward the edge, exactly as it did the Statistics header. Glyphs
    # went from ~103x24 to 87x19 and the centre moved from x87 to x63. back_game
    # scores 0.569 on the live 363 screen against 0.763 on the 353-era capture.
    #
    # This one was NOT cosmetic. On About, back_game was the ONLY _LANDMARKS
    # entry that matched, so when it stopped matching, ui.lost() started
    # returning True on a perfectly healthy About screen — and lost() means "an
    # interstitial ate the screen", whose handler is ui.recover(): terminate and
    # relaunch. Every to_menu() out of About was therefore silently RESTARTING
    # the app, which hid the Dev Panel button and broke the openDebugTools ->
    # verifyVictory hand-off. The symptom looked like "the Unity build scoped the
    # QA unlock to About"; the cause was one stale crop.
    #
    # It is not About-only: on 363 the small green-felt back control is SHARED by
    # About (1.000), the Help page (0.827) and the VICTORY screen (0.992), so one
    # crop covers all three. A victory_back crop cut from the 353-era
    # VictoryClean.png used to live here and was deleted — it scored 0.529 on the
    # live 363 victory screen, i.e. it matched nothing. Screens with a back on a
    # coloured BAR (Options, More Games, Statistics) are a different control.
    "about_back":      ("SpiderAboutPage.png", (11, 122, 106, 149)),
    # Same defect, same build, different bar: the Statistics header's back also
    # shrank on 363 (glyphs 79x19), and it sits on the DARK RED top bar rather
    # than About's green felt, so about_back only reaches 0.652 on it. Stats was
    # the fourth screen where ui.lost() misfired. Note about_back does cover the
    # HELP screen (0.827) — Help's bar is close enough — so three of the four
    # misfiring screens are handled by one crop plus a difficulty_easy landmark.
    "stats_back":      ("StatsPage.png", (19, 120, 106, 147)),

    # ── Last Score ("Last Won Game Score", the ranking view) ──────
    # Reached from the DIFFICULTY PICKER's bottom-left label, not from the main
    # menu — the Obj-C baselines' README calls it "reached from the menu", which
    # is one screen off for the Unity build.
    #
    # Source re-captured on build 363: 353 drew this label ~18 px lower
    # (y 1450-1482 vs 1433-1454 here), the same downward menu drift that already
    # forced game_center and about_back to be re-cut.
    "last_score":        ("DifficultyLevels.png", (90, 1428, 356, 1460)),
    # The screen's header, and the ONLY thing that identifies this screen: its
    # ranking BODY is shared with the victory screen, so screen_victory (0.99),
    # victory_ranking, victory_leaderboards and victory_achieve all match here
    # too — measured, not assumed. Anchor on the header or you cannot tell a
    # Last Score screen from a victory screen.
    #
    # This crop is also the header-TEXT assertion tests/visitLastScore.py makes.
    # Unity publishes no accessibility text, so "the header reads Last Won Game
    # Score" can only be answered by matching the pixels of those words. It
    # scores 1.000 on its own screen and 0.448 on the next-best capture in the
    # set, so the words are what is being matched, not the red bar.
    "screen_last_score": ("LastScore.png", (214, 114, 613, 150)),
    # The forward arrow beside the "ranking for <period>" line. Tapping it cycles
    # the period week -> month -> overall -> day -> week, so four taps are a full
    # round trip back to where you started.
    #
    # It is a plain triangle with almost no internal detail, which is the worst
    # case for template matching: it reaches 0.685 on the About screen and 0.655
    # on the game table against 1.000 here, i.e. only 0.015 of daylight under the
    # default 0.7. It therefore carries a raised THRESH in unity_ui.py. The 0.941
    # it scores on the victory screen is NOT a false positive — that screen
    # carries the same period stepper.
    "last_score_next":   ("LastScore.png", (645, 684, 686, 718)),

    # ── Game Center (Apple's own sheet, opened by "leaderboards") ─
    # NOT Unity content: this is GameKit's leaderboard UI, presented out of
    # process. WDA sees nothing but anonymous XCUIElementTypeOther over it — the
    # same blindness as the ATT prompt — so it can only be matched as an image,
    # and it scales by POINT density, not by Unity's width ratio. Both entries
    # are therefore listed in unity_ui.NATIVE_UI.
    #
    # The sheet's own big header. 1.000 here against 0.442 for the next-best
    # capture, and only 0.377 against the Game Center DASHBOARD's smaller
    # "Leaderboards" row — the two do not collide.
    "gc_leaderboards":   ("GameCenterLeaderboards.png", (38, 320, 482, 382)),
    # The circular back chevron, top-left of that sheet. 1.000 here, 0.573 next.
    # Caveat worth knowing: the circle is TRANSLUCENT, so this crop bakes in the
    # dark red bar that sat behind it. That is safe for the one flow that uses it
    # (the sheet is always opened from the Last Score screen, whose header is
    # that bar) and would need re-cutting to be used from anywhere else — the
    # same trap the iOS alert templates fell into.
    "gc_back":           ("GameCenterLeaderboards.png", (30, 102, 124, 194)),
    # The sister sheet, opened by "achievements". Same chrome, same back arrow in
    # the same place (gc_back scores 1.000 on both) — only the header differs, so
    # the header is what has to separate them, and it does: each scores 1.000 on
    # its own page and ~0.53 on the other's.
    "gc_achievements":   ("GameCenterAchievements.png", (35, 318, 494, 382)),

    # ── card suit pips, for the "Use Hearts" check ────────────────
    # The big suit symbol on a face-up card. Easy is a ONE-SUIT game, so with
    # Options' "Use Hearts" off every card is a black spade and with it on every
    # card is a red heart — which is what tests/verifyGamePlay.py reads off the
    # table to prove the setting reached the running game.
    #
    # Both sources are the SAME DEAL, captured either side of the toggle (ranks
    # 7,6,K,4,7,A,10,4,9,5 in both), so the crops differ only in the suit. That
    # also happens to be the proof the setting applies live rather than on the
    # next deal.
    #
    # Cut to the pip alone, clear of the corner glyph above it. Measured inside
    # board_box(): spade 1.000 / heart 0.498 on a spades table, spade 0.614 /
    # heart 1.000 on a hearts table — both a long way from the 0.70 threshold,
    # in the right direction each time. card_spade also scores 0.999 against a
    # build-353 capture, so it is not build-brittle.
    #
    # Note both DO match the ghost tableau art behind the main menu (0.87 / 0.81)
    # — real cards, wrong screen. Harmless here because the check only ever looks
    # inside the game table's board_box, but do not reuse these full-screen.
    "card_spade":        ("GamePlaySpades.png", (16, 536, 78, 600)),
    "card_heart":        ("GamePlayHearts.png", (16, 536, 78, 600)),

    # ── Options rows: the settings controls themselves ────────────
    # Every row on the Options page is <icon> <label> <control>, with the
    # control right-aligned in a fixed column. These crops are the LABELS: they
    # are the only part of a row with distinctive art, and unity_ui's
    # opt_* helpers read the control out of the pixels beside a matched label
    # rather than at a blind offset from the section header. That matters
    # because the two control kinds (toggle, slider) look nothing alike and a
    # test wants to name the row it is exercising.
    #
    # Rows above the fold come from OptionsPage.png; the rest from
    # OptionsPageBottom.png, the same screen scrolled to the end (capture it
    # with scripts/capture_unity_screens.py or by hand — see tests/README.md).
    "opt_applause":       ("OptionsPage.png", (135, 326, 465, 364)),
    "opt_effects":        ("OptionsPage.png", (136, 571, 425, 604)),
    "opt_auto_mute":      ("OptionsPage.png", (135, 799, 485, 832)),
    "opt_card_spacing":   ("OptionsPage.png", (136, 1112, 415, 1191)),
    "opt_card_bouncing":  ("OptionsPage.png", (136, 1365, 415, 1405)),
    "opt_card_lowering":  ("OptionsPage.png", (136, 1671, 417, 1711)),
    "opt_advanced":       ("OptionsPageBottom.png", (312, 1509, 515, 1542)),
    "opt_status_bar":     ("OptionsPageBottom.png", (137, 323, 450, 356)),
    "opt_card_messages":  ("OptionsPageBottom.png", (138, 549, 530, 588)),
    "opt_brightness":     ("OptionsPageBottom.png", (135, 770, 404, 810)),
    "opt_rich_features":  ("OptionsPageBottom.png", (136, 993, 403, 1026)),
    "opt_use_hearts":     ("OptionsPageBottom.png", (135, 1216, 348, 1248)),
    "opt_game_center":    ("OptionsPageBottom.png", (136, 1614, 380, 1646)),
}

PROFILES = {
    "iphone14": {"src": os.path.join(ROOT, "log", "ip14_unity_343"),
                 "out": os.path.join(ROOT, "iphone14", "assets_unity"),
                 "crops": CROPS},
    "iphone11": {"src": os.path.join(ROOT, "log", "unity_screens"),
                 "out": os.path.join(ROOT, "assets_unity"),
                 "crops": CROPS_IP11},
}


def main():
    check = "--check" in sys.argv
    global SRC, OUT
    prof = "iphone14"
    if "--device" in sys.argv:
        prof = sys.argv[sys.argv.index("--device") + 1]
    if prof not in PROFILES:
        sys.exit(f"unknown --device {prof}; pick from {', '.join(PROFILES)}")
    SRC, OUT, crops = (PROFILES[prof]["src"], PROFILES[prof]["out"],
                       PROFILES[prof]["crops"])
    print(f"profile {prof}:  {SRC} -> {OUT}")

    os.makedirs(OUT, exist_ok=True)
    missing_src = set()
    n = 0
    for name, (src, box) in sorted(crops.items()):
        path = os.path.join(SRC, src)
        if not os.path.exists(path):
            missing_src.add(src)
            continue
        dst = os.path.join(OUT, name + ".png")
        if check:
            print(f"  {'ok ' if os.path.exists(dst) else 'MISSING'} {name}")
            continue
        im = Image.open(path).crop(box)
        im.save(dst)
        n += 1
        print(f"  wrote {name}.png  {im.size[0]}x{im.size[1]}  from {src}")
    if missing_src:
        print(f"\n  !! missing source captures: {', '.join(sorted(missing_src))}")
    if not check:
        print(f"\n  {n} templates -> {OUT}")


if __name__ == "__main__":
    main()
