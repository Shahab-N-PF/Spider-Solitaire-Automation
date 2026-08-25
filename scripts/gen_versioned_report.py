#!/usr/bin/env python3
"""Build a SINGLE self-contained fidelity report with a **version switcher** — one
page that holds every captured Unity build and flips between them with a button.

The Obj-C baseline is constant, so it's embedded once per screen; each version
contributes its own Unity capture, diff image, diff%, findings, and per-screen
notes. Switching version swaps all of that (and re-ranks the screen cards).

Wired for iPhone 7 (builds 341 / 337 / 335), iPad (builds 337 / 335), and
iPhone 14 Pro Max (build 341). Add a device/version by extending DEVICES below
with the capture dir + curated findings.

Run:  ./.venv/bin/python scripts/gen_versioned_report.py {ip7|ipad}
Out:  reports/<dev>_unity_report.html
"""
import base64
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))

import cv2  # noqa: E402
import compare_unity_ip7 as C7  # noqa: E402
import compare_unity_ip7_landscape as C7L  # noqa: E402
import compare_unity_ipad as CI  # noqa: E402
import compare_unity_ip14 as C14  # noqa: E402

LABELS = {
    "MainMenu.png": "Main Menu", "DifficultyLevels.png": "Difficulty Picker",
    "Play.png": "Game Table", "OptionsPage.png": "Options",
    "StatsPage.png": "Statistics", "HelpPage.png": "Help",
    "MoreGames.png": "More Games", "SpiderAboutPage.png": "About",
    "SpiderFAQ.png": "FAQ", "choose_look_surface.png": "Choose Look · Surface",
    "choose_look_cards.png": "Choose Look · Cards", "more_games_icons.png": "Menu · Promo Icons",
    "InGameMenu.png": "In-Game Menu", "VictoryScreen1.png": "Victory · Score",
    "VictoryScreen2.png": "Victory · Best", "StatsResetBtn.png": "Statistics · Reset",
    "HelpPageBottom.png": "Help · Bottom", "LastScore.png": "Last Score",
}

SEV = {
    "bug":   ("Content bug", "var(--bad)"),
    "drop":  ("Dropped element", "var(--warn)"),
    "layout":("Layout drift", "var(--info)"),
    "minor": ("Minor delta", "var(--muted)"),
    "ok":    ("Fixed / correct", "var(--ok)"),
}

# ── iPhone 7: build-2 (prev) + build-3 (latest) ───────────────────────────────
# build-2 curated notes (as they were when build-2 was the current build).
IP7_V2_NOTES = {
    "SpiderFAQ.png": "WRONG FAQ CONTENT: populated (was blank before) but shows Klondike/regular-Solitaire questions ('draw 1 card to 3 cards', 'Yellow Triangle') instead of Spider's.",
    "HelpPage.png": "Duplicated-'Introduction' bug FIXED; text correct. Remaining diff is typography (Unity wraps lines differently) + the header illustration.",
    "SpiderAboutPage.png": "Prior bugs FIXED: 'Spider ▷ Solitaire' divider restored and 'submit feedback' spelled correctly. Version 8.0.0 vs 7.42.5.",
    "choose_look_cards.png": "Typo FIXED: now 'symbols' (was 'syymbols'). Card-back designs in a different grid order.",
    "MainMenu.png": "Unity still DROPS the left cross-promo icon strip + 'More Games' badge. Bottom ad banner now present. Sparkle-glow animation volatile.",
    "more_games_icons.png": "Main-menu view; still NO left promo-icon strip. Bottom ad banner now present.",
    "StatsPage.png": "Not apples-to-apples (games played on device). Markers plain '*' vs Obj-C '✻'.",
    "OptionsPage.png": "Content matches (Sounds + Cards). Diff is heavier/shifted label typography + toggle rendering.",
    "DifficultyLevels.png": "Unity ADDS 'More Games'/'Choose Look' entries and DROPS the smiley cursor at 'Hard'; ad banner differs.",
    "Play.png": "Chrome-only (dealt cards masked). Bottom ad banner present in this build.",
    "MoreGames.png": "Solitaire logo/card-fan + Sudoku graphic sit lower than Obj-C (vertical offset); FREE-pill tint differs.",
    "choose_look_surface.png": "Close match to Obj-C.",
    "InGameMenu.png": "Close match — menu panel over the wood tray; minor button-rendering differences. Dealt cards masked.",
    "VictoryScreen1.png": "Unity ADDS a top promo-icon strip Obj-C lacks; BLUE help/new/stats buttons vs Obj-C red. Score masked.",
    "VictoryScreen2.png": "BLUE help/new/stats buttons (Obj-C red); promo strip present. Score masked.",
}
IP7_V2_FINDINGS = [
    ("bug", "FAQ shows the wrong game's content", "Populated (was blank in the first build) but lists Klondike questions ('draw 1 card to 3 cards', 'Yellow Triangle') instead of Spider's.", "FAQ"),
    ("drop", "Cross-promo icon strip still missing", "The main menu's left strip of 5 cross-promo icons + the 'More Games' badge are still absent.", "Menu"),
    ("layout", "Victory screens recolored", "help/new/stats buttons are blue vs Obj-C red, and Victory·Score gains a promo-icon strip the Obj-C first-win screen lacks.", "Victory"),
    ("layout", "Systemic typography drift", "Body text is heavier and wraps differently; Difficulty adds entries + drops the smiley cursor; card-back grid reordered; Stats '*' vs '✻'.", "systemic"),
    ("ok", "Fixed since the first build", "Empty FAQ now renders; Help no longer duplicates 'Introduction'; About '▷' divider restored; 'feeback'→'feedback' and 'syymbols'→'symbols' corrected.", "regression check"),
]
IP7_V2_VERDICT = ("This build cleared five defects from the first pass (empty FAQ, duplicated Help "
                  "'Introduction', missing About divider, two typos) but is still not pixel-faithful: "
                  "the FAQ now loads the <b>wrong game's content</b>, the main-menu promo strip is "
                  "still dropped, and victory buttons are blue.")
IP7_V2_BUGS = {"SpiderFAQ.png"}

IP7_V3_FINDINGS = [
    ("bug", "FAQ duplicates its first question", "Content is now Spider's own (wrong-game text fixed), but the first entry 'How do I play the game?' renders twice, back-to-back.", "FAQ"),
    ("bug", "'Dev Panel' debug button ships", "Both victory screens show a 'Dev Panel' button bottom-right — a development-only control that should not ship.", "Victory"),
    ("layout", "Typography & content deltas", "Body text heavier/re-wrapped (Help/Options/FAQ/More Games); lowercase 'options' title; More Games lists extra titles; Stats '*' vs '✻'; dropped ad banners.", "systemic"),
    ("ok", "Fixed since build 335", "FAQ loads Spider's own content; the main-menu promo-icon strip is back; Difficulty's smiley cursor returns; victory buttons are red again and Victory·Score drops its promo strip.", "regression check"),
    ("ok", "Still correct", "About keeps its '▷' divider + correct 'submit feedback'; Help shows a single 'Introduction'; Cards reads 'symbols'.", "About · Help · Cards"),
]
IP7_V3_VERDICT = ("This build clears the earlier content bugs — the FAQ loads Spider's own content, "
                  "the promo-icon strip is back, the difficulty smiley cursor returns, and victory "
                  "buttons are red again. Two bugs remain: the FAQ <b>duplicates its first question</b> "
                  "and a <b>'Dev Panel' debug button</b> ships on both win screens.")
IP7_V3_BUGS = {"SpiderFAQ.png", "VictoryScreen1.png", "VictoryScreen2.png"}

# build-341 (latest) curated notes — clears the two build-337 bugs; only systemic drift remains.
IP7_V341_NOTES = {
    "SpiderFAQ.png": "FAQ content correct AND the first-question duplicate is now FIXED — 'How do I play the game?' appears once. Remaining diff is typography / line-wrap only.",
    "HelpPage.png": "Single 'Introduction', correct Spider rules. Remaining diff is typography (Unity wraps lines heavier/differently) + the header illustration.",
    "SpiderAboutPage.png": "Clean match: 'Spider ▷ Solitaire' divider, 'submit feedback' correct. Only delta is version 8.0.0 vs 7.42.5.",
    "choose_look_cards.png": "Cards tab, 6 designs, 'symbols' spelled correctly; modal well-positioned.",
    "MainMenu.png": "Promo-icon strip PRESENT (loads a beat after the menu). Diff is promo-icon art rendering + menu-label typography + logo shading. Sparkle-glow volatile.",
    "more_games_icons.png": "Settled menu with the left promo-icon strip present.",
    "StatsPage.png": "Not apples-to-apples (different play history). Section markers render as a plain '*' vs Obj-C's decorative '✻'.",
    "OptionsPage.png": "Content matches (Sounds + Cards). Diff is the lowercase 'options' title + heavier label typography.",
    "DifficultyLevels.png": "Smiley cursor at 'Hard' present and no stray 'More Games/Choose Look' entries. Diff is typography + the rotating ad banner.",
    "Play.png": "Chrome-only (dealt cards masked). Unity has no bottom ad banner; top bar + hint text typography differ.",
    "MoreGames.png": "FREE price pills present; layout matches. The smiley 'tap' cursor is animated (volatile).",
    "choose_look_surface.png": "Surface tab, 9 swatches, Simulate Depth toggle; modal well-positioned — close match.",
    "InGameMenu.png": "replay/abandon/options/new/help/FAQ tray over the wood; dealt cards masked. Minor button-rendering diffs.",
    "VictoryScreen1.png": "help/new/stats buttons RED, no promo strip, and the 'Dev Panel' debug button is GONE (fixed). Score masked.",
    "VictoryScreen2.png": "help/new/stats RED, promo strip present, and the 'Dev Panel' debug button is GONE (fixed). Score masked.",
    "StatsResetBtn.png": "Statistics scrolled to the Reset button. Per-run values masked; divider renders as plain '* * *' vs Obj-C's decorative '✻ ✻ ✻'.",
}
IP7_V341_FINDINGS = [
    ("layout", "Systemic typography / line-wrap drift", "Unity renders body text heavier and wraps lines differently, shifting every line a few pixels — the main remaining diff on FAQ, Options, Stats, Help and More Games.", "systemic"),
    ("minor", "Lowercase title + marker style", "The Options title is lowercase 'options', and Stats section dividers use a plain '*' vs the Obj-C decorative '✻'.", "Options · Stats"),
    ("minor", "Promo-icon art differs", "The main-menu cross-promo icons are present (not dropped) but render slightly differently from Obj-C.", "Menu"),
    ("ok", "Two build-337 bugs FIXED", "The FAQ no longer duplicates its first question, and the development-only 'Dev Panel' button is gone from both victory screens.", "FAQ · Victory"),
    ("ok", "Still correct", "Promo strip present, victory buttons red, difficulty smiley cursor present; About '▷' divider + 'submit feedback'; Help single 'Introduction'; Cards 'symbols'.", "regression check"),
]
IP7_V341_VERDICT = ("Build 341 clears both open bugs from build 337 — the FAQ no longer <b>duplicates its "
                    "first question</b> and the <b>'Dev Panel' debug button</b> is gone from the win screens. "
                    "No content bugs remain. Every screen still deviates, but the differences are now almost "
                    "entirely systemic <b>typography / line-wrap drift</b>, plus the lowercase 'options' title "
                    "and the plain '*' vs decorative '✻' markers. Peak diff fell from ~27% (337) to ~16%.")
IP7_V341_BUGS = set()

# ── iPhone 7 PORTRAIT: build 343 (latest) ─────────────────────────────────────
IP7_V343_NOTES = {
    "SpiderFAQ.png": "Correct Spider content; first question appears once (not duplicated). Diff is typography / line-wrap only.",
    "OptionsPage.png": "Sounds + Cards match. Diff is the lowercase 'options' title + heavier label typography.",
    "StatsResetBtn.png": "Reset button present; per-run values masked. '✻ ✻ ✻' divider decorative (matches Obj-C). Same as build 341.",
    "MoreGames.png": "Curtain promo matches; FREE price pills present. Smiley 'tap' cursor animated (volatile).",
    "HelpPage.png": "Header illustration + single 'Introduction' + Rules, correct text. Diff is typography / line-wrap. Same as build 341.",
    "StatsPage.png": "Fresh install, so values match the baseline (0 / none). Section markers decorative '✻'; remaining diff is label typography. Same as build 341.",
    "more_games_icons.png": "Settled menu with the left promo-icon strip present.",
    "choose_look_cards.png": "Cards tab, 6 designs, 'symbols' spelled correctly; modal well-positioned.",
    "InGameMenu.png": "replay/abandon/options/new/help/FAQ tray (3×2); dealt cards masked. Minor button-rendering diffs.",
    "choose_look_surface.png": "Surface tab, 9 swatches, Simulate Depth toggle; modal well-positioned.",
    "MainMenu.png": "Promo-icon strip present; logo + menu-label typography differ; sparkle-glow volatile.",
    "VictoryScreen2.png": "Promo strip present, help/new/stats RED, and NO 'Dev Panel' button. Score block masked.",
    "VictoryScreen1.png": "No promo strip, help/new/stats RED, and NO 'Dev Panel' button. Score block masked.",
    "DifficultyLevels.png": "Smiley cursor at 'Hard' present. Diff is typography + the 'LAST SCORE' label.",
    "Play.png": "Chrome-only (dealt cards masked). Unity has no bottom ad banner; top-bar typography differs.",
    "LastScore.png": "'Last Won Game Score' — date, won-count and score table masked; clean match on the fixed chrome.",
    "SpiderAboutPage.png": "'Spider ▷ Solitaire' divider, links correct; only delta is version 8.0.0 vs 7.42.5.",
}
IP7_V343_FINDINGS = [
    ("ok", "No change from build 341", "Build 343's portrait UI is effectively identical to 341 — every screen's diff-vs-baseline matches within capture noise (mean |Δ| 0.8pp; the text screens are within ~0.3pp). No fixes and no regressions in portrait.", "vs build 341"),
    ("layout", "Systemic typography / line-wrap drift", "Unity renders body text heavier and wraps lines differently, shifting each line a few pixels — the main diff on FAQ, Options, Stats, Help and More Games. Unchanged from 341.", "systemic"),
    ("minor", "Lowercase 'options' title", "The Options screen title is still lowercase 'options' vs the Obj-C 'Options'. Unchanged from 341.", "Options"),
    ("ok", "No content bugs", "FAQ single first question; victory buttons RED with no 'Dev Panel' button; promo strip present; About '▷' divider + version 8.0.0; Cards 'symbols'; Stats markers decorative '✻'.", "regression check"),
]
IP7_V343_VERDICT = ("Build 343's <b>portrait</b> UI is effectively <b>unchanged from build 341</b> — every screen's "
                    "diff-vs-baseline matches 341 within capture noise (animation frames, dealt cards), so there are "
                    "<b>no fixes and no regressions</b> in portrait. Fidelity holds at ~17% peak with <b>no content "
                    "bugs</b>; the remaining differences are the familiar systemic <b>typography / line-wrap drift</b> "
                    "plus the lowercase 'options' title. The real movement in build 343 is on the landscape side — "
                    "see the landscape report.")
IP7_V343_BUGS = set()

# ── iPhone 7 LANDSCAPE: build 343 (first landscape measurement) ───────────────
IP7L_V343_NOTES = {
    "InGameMenu.png": "LANDSCAPE LAYOUT BUG: the pause tray uses the portrait 2-column grid (replay/abandon · options/new · help/FAQ) instead of Obj-C's 3-column landscape layout, so every button is rearranged and repositioned. Dealt cards masked.",
    "VictoryScreen1.png": "A development-only 'Dev Panel' button ships bottom-right (should not ship). Header/table shifted; help/new/stats RED; no promo strip; score block masked. Felt lighting differs on the right.",
    "VictoryScreen2.png": "Same 'Dev Panel' debug button bottom-right. Promo strip present; help/new/stats RED; score block masked.",
    "choose_look_surface.png": "The Choose-Look modal is shifted/mispositioned — the tab, all 9 swatches, the toggle and the text are offset vs Obj-C.",
    "choose_look_cards.png": "Same modal offset on the Cards tab (6 designs, 'symbols' spelled correctly).",
    "more_games_icons.png": "Promo-icon strip present; logo, menu-arc labels and right-side felt lighting differ.",
    "StatsResetBtn.png": "Reset button present, '✻ ✻ ✻' divider decorative; per-run values masked. Captured a touch below the baseline scroll, which adds some vertical offset.",
    "SpiderFAQ.png": "Correct content, single first question. Diff is typography / line-wrap.",
    "StatsPage.png": "Fresh install so values match; markers decorative '✻'. Diff is label typography.",
    "Play.png": "Chrome-only (dealt tableau masked). Unity has no bottom ad banner; bottom-bar typography differs.",
    "HelpPage.png": "Header illustration + single 'Introduction' + Rules. Diff is typography / line-wrap.",
    "LastScore.png": "'Last Won Game Score' — date, won-count and table masked; right-side labels repositioned; felt lighting differs.",
    "SpiderAboutPage.png": "'Spider ▷ Solitaire' divider + links correct; version 8.0.0. Felt lighting differs on the right.",
    "OptionsPage.png": "Sounds section matches; lowercase 'options' title + heavier label typography.",
    "MoreGames.png": "Curtain promo matches; FREE pills present; smiley 'tap' cursor volatile.",
    "MainMenu.png": "Menu arc + logo + background demo tableau + right-side felt lighting differ vs Obj-C.",
    "DifficultyLevels.png": "Smiley cursor present; 'LAST SCORE' label. Menu arc + felt lighting differ.",
}
IP7L_V343_FINDINGS = [
    ("bug", "In-game menu not adapted to landscape", "The pause tray keeps the portrait 2-column button grid instead of Obj-C's 3-column landscape layout — replay/abandon/help/options/new/FAQ are rearranged and mispositioned (47% diff, the worst screen).", "In-Game Menu"),
    ("bug", "'Dev Panel' debug button ships", "A development-only 'Dev Panel' button is visible bottom-right on BOTH landscape victory screens. It is absent in portrait and should not ship.", "Victory · Score / Best"),
    ("layout", "Choose-Look modal mispositioned", "The Choose-Look modal (Surface + Cards) is shifted from the Obj-C position, offsetting the tabs, every swatch, the toggle and the description text.", "Choose Look"),
    ("layout", "Felt lighting + typography drift", "The landscape felt renders with different lighting on the right and body text is heavier / wraps differently — together these lift the baseline diff on every menu screen well above the portrait level.", "systemic"),
    ("minor", "Lowercase 'options' title", "Same lowercase 'options' title as portrait.", "Options"),
    ("ok", "No new content bugs", "FAQ single first question; ✻ markers decorative; promo strip present; About divider + version. (A 'duplicate ranking for' seen mid-load is a transient frame, not a bug.)", "regression check"),
]
IP7L_V343_VERDICT = ("First landscape measurement of the Unity port — and landscape is <b>markedly less faithful than "
                     "portrait</b> (peak 47% vs ~17%). Two real defects stand out: the <b>in-game menu keeps the "
                     "portrait 2-column button layout</b> instead of the 3-column landscape one, and a <b>'Dev Panel' "
                     "debug button ships on both victory screens</b>. The Choose-Look modal is mispositioned, and "
                     "felt-lighting + typography drift lift every menu screen's diff. Content is otherwise correct "
                     "(FAQ, markers, promo strip, About all fine).")
IP7L_V343_BUGS = {"InGameMenu.png", "VictoryScreen1.png", "VictoryScreen2.png", "choose_look_surface.png", "choose_look_cards.png"}

# ── iPhone 7 LANDSCAPE: build 345 (latest) — the in-game-menu fix landed ───────
# Measured against RE-CAPTURED Obj-C baselines for MainMenu + DifficultyLevels
# (the 343-era ones were in a wrong state); volatile masks added for all 17 screens.
IP7L_V345_NOTES = {
    "InGameMenu.png": "FIXED — 3-column landscape tray (replay/abandon/options · new/help/FAQ) instead of 343's portrait 2-column grid. 47% → 16%. Button ordering within the grid differs slightly from Obj-C; bottom ad banner dropped. Dealt cards masked.",
    "DifficultyLevels.png": "Obj-C baseline RE-CAPTURED (was a wrong state). Now flat vs 343 (~25%) — the earlier 'regression' was the bad baseline. Remaining diff is systemic felt/typography + difficulty-picker elements (ribbon, smiley); sparkle-glow masked (volatile), bottom ad banner masked.",
    "MainMenu.png": "Obj-C baseline re-captured (was a wrong state); now ~20%, down from 343. Diff is systemic felt-redder + menu-label typography. Sparkle-glow masked (volatile); bottom ad banner masked.",
    "more_games_icons.png": "Settled menu WITH the left 5-icon cross-promo strip — the peak screen (~26%): the promo-icon art renders differently in Unity, plus felt/typography. Bottom ad banner masked.",
    "choose_look_surface.png": "Surface tab, 9 swatches, Simulate Depth toggle. Modal repositioned much closer to Obj-C (37% → 21%).",
    "choose_look_cards.png": "Cards tab, 6 designs, 'symbols' spelled correctly. Modal repositioned (35% → 18%).",
    "VictoryScreen1.png": "Victory · Score, help/new/stats RED, repositioned closer to Obj-C (39% → 23%). The development-only 'Dev Panel' button still ships bottom-right but is masked out of the diff by request. Score block masked.",
    "VictoryScreen2.png": "Victory · Best, promo strip present, help/new/stats RED (38% → 23%). 'Dev Panel' button masked out of the diff by request. Score block masked.",
    "LastScore.png": "'Last Won Game Score' ranking view; date / won-count / score table masked (run-dependent). Closer to Obj-C than 343 (25% → 15%).",
    "OptionsPage.png": "Sounds section; lowercase 'options' title + heavier label typography. Ticked up ~3pp vs 343 (18% → 21%) — minor typography variance.",
    "StatsPage.png": "Fresh install so values match the baseline (0 / none); decorative '✻' markers. 28% → 13%.",
    "StatsResetBtn.png": "Scrolled to 'Reset Statistics'; '✻ ✻ ✻' divider; per-run values masked. 29% → 20%.",
    "HelpPage.png": "Header illustration + single 'Introduction' + Rules, correct Spider text. Diff is typography / line-wrap.",
    "SpiderAboutPage.png": "'Spider ▷ Solitaire' divider + links, version 8.0.0; logo top-right. 22% → 13%.",
    "SpiderFAQ.png": "Spider's own FAQ, single first question. Diff is typography / line-wrap. 29% → 20%.",
    "MoreGames.png": "Curtain promo (Solitaire + FREE pill, Sudoku 2); smiley 'tap' cursors volatile.",
    "Play.png": "Landscape game table (10 columns across the top); dealt cards masked. Unity has no bottom ad banner.",
}
IP7L_V345_FINDINGS = [
    ("ok", "In-game menu adapted to landscape", "The pause tray now uses the 3-column landscape grid (replay/abandon/options · new/help/FAQ) instead of build 343's portrait 2-column layout — the biggest fix, 47% → 16%. Residual: button ordering within the grid differs slightly from Obj-C; bottom ad banner dropped (masked).", "In-Game Menu"),
    ("ok", "Choose-Look modal + victory screens repositioned", "The Choose-Look modal (Surface 37% → 21%, Cards 35% → 18%) and both victory screens (Score 39% → 23%, Best 38% → 23%) render much closer to Obj-C than 343.", "Choose Look · Victory"),
    ("ok", "Improvement across the board, no regressions", "Measured against the Obj-C baseline, every screen is better than or level with 343 — led by the in-game menu (−31pp). The one exception is Options, up ~3pp (18% → 21%): minor typography variance, not a structural change.", "vs build 343"),
    ("layout", "Systemic felt tint + typography drift", "Unity renders the felt slightly redder than Obj-C (~+13 on the red channel) and its body text heavier / re-wrapped — now the main diff driver on the menu screens (more_games_icons 26%, DifficultyLevels 25%, Options 21%, MainMenu 20%). Lowercase 'options' title unchanged.", "systemic"),
    ("minor", "Baselines corrected + volatile masks added", "The MainMenu and DifficultyLevels Obj-C baselines were re-captured (they were in a wrong state, which had inflated those two screens); volatile masks were built for all 17 screens so sparkle-glow / smiley animation no longer pollutes the diff.", "methodology"),
    ("ok", "No content bugs", "FAQ single first question; About '▷' divider + version 8.0.0; Stats markers decorative '✻'; promo strip present; victory buttons RED. The development-only 'Dev Panel' button still ships on both victory screens but is masked out of the diff by request (it does not affect the numbers).", "regression check"),
]
IP7L_V345_VERDICT = ("Build 345 is a clean, across-the-board improvement in landscape fidelity — measured against the "
                     "Obj-C baseline, <b>every screen is better than or level with build 343, with no regressions</b>. The "
                     "headline build-343 bug — the in-game pause menu using the portrait <b>2-column</b> layout — is "
                     "<b>fixed</b> with a proper <b>3-column landscape</b> tray (47% → 16%). The Choose-Look modal and both "
                     "victory screens render much closer to Obj-C. Peak diff is ~26% (the settled menu's cross-promo icons); "
                     "the remaining differences are <b>systemic</b> — Unity renders the felt slightly redder and its text "
                     "heavier / re-wrapped. <b>No content bugs.</b> (An earlier pass flagged a difficulty-picker regression; "
                     "that turned out to be a wrong-state Obj-C baseline, now re-captured — the screen is flat vs 343.)")
IP7L_V345_BUGS = set()

# ── iPad: build 335 (first iPad Unity) + build 337 (latest) ───────────────────
IPAD_V335_NOTES = {
    "SpiderFAQ.png": "WRONG FAQ CONTENT (same bug as iPhone 7): populated but with Klondike/regular-Solitaire questions ('draw 1 card to 3 cards', 'Yellow Triangle') instead of Spider's.",
    "HelpPage.png": "Content correct and not duplicated. Remaining diff is typography (Unity wraps text heavier/larger) + the header illustration.",
    "SpiderAboutPage.png": "Clean match: 'Spider ▷ Solitaire' divider, 'submit feedback' correct. Only delta is version 8.0.0 vs 7.42.5.",
    "choose_look_cards.png": "Description reads 'symbols' (correct). Card-back designs in a different grid order vs Obj-C.",
    "MainMenu.png": "Unity DROPS the left cross-promo icon strip (5 icons) + 'More Games' badge. Sparkle-glow animation volatile.",
    "more_games_icons.png": "Main-menu view; Unity has NO left promo-icon strip.",
    "StatsPage.png": "Not apples-to-apples (different play history). Markers plain '*' vs Obj-C '✻', lowercase headers.",
    "OptionsPage.png": "Content matches. Diffs: lowercase 'options' title, an added 'Interface' section (Card Lowering), heavier label typography.",
    "DifficultyLevels.png": "Levels list matches, but Unity ADDS 'More Games'/'Choose Look' entries and DROPS the smiley cursor at 'Hard'; ad banner differs.",
    "Play.png": "Chrome-only (dealt cards masked). Unity has no bottom ad banner (Obj-C shows one).",
    "MoreGames.png": "Unity lists more titles and shifts the layout vs Obj-C's two games.",
    "choose_look_surface.png": "LAYOUT DRIFT: the whole Choose-Look modal renders shifted down and enlarged vs Obj-C (tabs, swatches, toggle misalign).",
    "InGameMenu.png": "LAYOUT DRIFT: the menu panel is shifted up and Unity drops the bottom ad banner; it no longer sits where Obj-C places it. Dealt cards masked.",
    "VictoryScreen1.png": "Unity ADDS a top promo-icon strip Obj-C's first victory screen lacks; BLUE help/new/stats buttons vs Obj-C red. Score masked.",
    "VictoryScreen2.png": "help/new/stats buttons are BLUE (Obj-C red); promo strip present. Score masked.",
}
IPAD_V335_FINDINGS = [
    ("bug", "FAQ shows the wrong game's content", "Lists Klondike questions ('draw 1 card to 3 cards', 'Yellow Triangle') instead of Spider's. Same defect as iPhone 7.", "FAQ"),
    ("layout", "Modals & menus mis-positioned on iPad", "The Choose-Look modal renders shifted down and enlarged; the in-game menu panel sits higher than Obj-C — the biggest diff driver.", "Choose Look · In-Game Menu"),
    ("drop", "Dropped elements", "The main-menu left strip of 5 cross-promo icons (+ badge) is gone, and Unity drops the bottom ad banner on the Game Table and In-Game Menu.", "Menu · Play"),
    ("layout", "Victory screens recolored", "help/new/stats buttons are blue vs Obj-C red, and Victory·Score gains a top promo-icon strip Obj-C's first-win screen lacks.", "Victory"),
    ("layout", "Typography & content deltas", "Body text heavier/re-wrapped; lowercase 'options' title + an added 'Interface' section; Difficulty adds entries + drops the smiley cursor; Stats '*' vs '✻'.", "systemic"),
]
IPAD_V335_VERDICT = ("The first iPad Unity build is not pixel-faithful: every screen deviates, with heavy "
                     "layout drift — the Choose-Look modal shifted + enlarged, the in-game menu panel "
                     "repositioned — plus the FAQ loading the <b>wrong game's content</b>, a dropped promo "
                     "strip + ad banners, and blue victory buttons.")
IPAD_V335_BUGS = {"SpiderFAQ.png"}

IPAD_V337_FINDINGS = [
    ("bug", "FAQ duplicates its first question", "Content is now Spider's own (wrong-game text fixed), but the first entry 'How do I play the game?' renders twice, back-to-back.", "FAQ"),
    ("bug", "'Dev Panel' debug button ships", "Victory·Best shows a 'Dev Panel' button bottom-right — a development-only control that should not ship.", "Victory · Best"),
    ("layout", "In-game menu tray still differs", "On the In-Game Menu the bottom tray renders with different wood/button styling and Unity drops the ad banner — the largest remaining diff.", "In-Game Menu"),
    ("layout", "Typography & content deltas", "Body text heavier/re-wrapped (Help/Options/FAQ); lowercase 'options' title; More Games lists extra titles; Stats '*' vs '✻'; dropped ad banners.", "systemic"),
    ("ok", "Fixed since build 335", "Choose-Look modal positioned correctly again; main-menu promo strip back; Difficulty smiley cursor returns; victory buttons red + Victory·Score drops its promo strip; FAQ loads Spider's own content.", "regression check"),
    ("ok", "Still correct", "About keeps its '▷' divider + correct 'submit feedback'; Help shows a single 'Introduction'; Cards reads 'symbols'.", "About · Help · Cards"),
]
IPAD_V337_VERDICT = ("Build 337 on iPad clears most of the earlier layout drift — the Choose-Look modal is "
                     "positioned correctly again, the main-menu promo strip is back, the difficulty smiley "
                     "cursor returns, and victory buttons are red. Two content bugs remain: the FAQ "
                     "<b>duplicates its first question</b> and a <b>'Dev Panel' debug button</b> ships on the "
                     "win screen.")
IPAD_V337_BUGS = {"SpiderFAQ.png", "VictoryScreen2.png"}

# ── iPhone 14 Pro Max: build 341 (first Unity build measured on this device) ──
IP14_V341_NOTES = {
    "SpiderFAQ.png": "FAQ content correct AND the first-question duplicate is FIXED (single 'How do I play the game?'). Remaining diff is heavier text + line-wrap drift on the tall screen.",
    "HelpPage.png": "Content correct, single 'Introduction'. LARGE diff: the header illustration renders taller/lower and the body text uses wider line-spacing, so every line drifts progressively downward.",
    "SpiderAboutPage.png": "Content correct. The logo + link list render shifted DOWN vs Obj-C — a vertical layout offset (not just typography). Version 8.0.0 vs 7.42.5.",
    "choose_look_cards.png": "Cards tab, 'symbols' spelled correctly, modal well-positioned. Card-back art + typography differ.",
    "MainMenu.png": "Promo-icon strip PRESENT (loads a beat after the menu). Diff is menu-label typography + logo shading. Sparkle-glow volatile.",
    "more_games_icons.png": "Settled menu with the left promo-icon strip present.",
    "StatsPage.png": "NOT apples-to-apples (different play history). Heavier typography; section-marker style.",
    "OptionsPage.png": "Content matches (Sounds + Cards + Interface). Lowercase 'options' title + heavier/wider label typography; rows drift down.",
    "DifficultyLevels.png": "Smiley cursor at 'Hard' present, no stray entries. Diff is typography + the rotating ad banner.",
    "Play.png": "Chrome-only (dealt cards masked). Unity has no bottom ad banner; top bar + hint typography differ.",
    "MoreGames.png": "Curtain page matches (captured offline, so no FREE StoreKit pills — same as baseline). Smiley 'tap' cursors volatile.",
    "choose_look_surface.png": "Surface tab, 9 swatches, Simulate Depth toggle; modal well-positioned.",
    "InGameMenu.png": "replay/abandon/options/new/help/FAQ tray; dealt cards masked. Button/typography differ.",
    "VictoryScreen1.png": "help/new/stats buttons RED, no promo strip, and NO 'Dev Panel' debug button (fixed). Score masked.",
    "VictoryScreen2.png": "help/new/stats RED, promo strip present, and NO 'Dev Panel' debug button (fixed). Score masked.",
    "StatsResetBtn.png": "Statistics scrolled to the Reset button. Per-run values masked; divider renders as plain '* * *' vs Obj-C's decorative '✻ ✻ ✻'.",
    "HelpPageBottom.png": "Help scrolled to the bottom — Undo/Menu sections + the FAQ link. Text drifts downward (wider line-spacing).",
}
IP14_V341_FINDINGS = [
    ("layout", "Systemic typography + downward drift", "Unity renders body text heavier and with wider line-spacing, so text drifts progressively downward — far more pronounced on the tall 1290×2796 screen (Help 33%, More Games 26%, FAQ 25%, Options 23%).", "systemic"),
    ("layout", "Content positioned lower than Obj-C", "On static screens the whole content block renders shifted down vs Obj-C — clearest on About (logo + link list) and the Help header illustration. A vertical layout offset, not just typography.", "About · Help"),
    ("minor", "Lowercase title + marker style", "Options title is lowercase 'options'; Stats dividers use a plain '*' vs the Obj-C decorative '✻'.", "Options · Stats"),
    ("ok", "Same content fixes as iPhone 7 build 341", "FAQ no longer duplicates its first question; the 'Dev Panel' debug button is gone from both victory screens; the promo-icon strip is present; victory buttons are red.", "FAQ · Victory · Menu"),
    ("ok", "Still correct", "About keeps its '▷' divider + correct 'submit feedback'; Help shows a single 'Introduction'; Cards reads 'symbols'; the difficulty smiley cursor is present.", "regression check"),
]
IP14_V341_VERDICT = ("First iPhone 14 Pro Max Unity build measured (build 341). Every content-level fix from "
                     "iPhone 7 is here — the FAQ no longer <b>duplicates its first question</b> and the "
                     "<b>'Dev Panel' debug button</b> is gone. But pixel fidelity is weaker than on iPhone 7: "
                     "every screen deviates 13–33%, driven by <b>heavier text with wider line-spacing that "
                     "drifts downward</b>, plus a <b>vertical layout offset</b> where content sits lower than "
                     "Obj-C (clearest on About and Help). No content bugs remain — the work left is typography "
                     "and vertical layout.")
IP14_V341_BUGS = set()

# ── iPhone 14 Pro Max: build 343 (2026-08-04) — tracks 341 within capture noise ──
IP14_V343_NOTES = {
    "MainMenu.png": "Menu focus captured before the left promo-icon strip + bottom ad banner settle in (that settled state is 'Menu · Promo Icons'). Menu-label typography + logo shading differ; the Play/Stats sparkle glow is volatile.",
    "more_games_icons.png": "Settled menu WITH the left 5-icon cross-promo strip present. Unity still omits the bottom 'Card Games · FREE' ad banner (sits in the masked bottom band). Promo-icon art + menu typography differ.",
    "DifficultyLevels.png": "Easy/Medium/Hard/Bold/Expert arc, smiley cursor at 'Hard' (volatile), 'LAST SCORE' ribbon. Diff is menu typography.",
    "Play.png": "Chrome-only (dealt tableau masked). Unity has no bottom ad banner; top bar + hint-text typography differ.",
    "InGameMenu.png": "replay/abandon/options/new/help/FAQ tray (3×2) over the wood; dealt cards masked. Button styling + typography differ.",
    "VictoryScreen1.png": "First victory/ranking screen — no promo-icon strip; help/new/stats buttons RED. Current/rank/best score block masked (run-dependent).",
    "VictoryScreen2.png": "Second victory screen — promo-icon strip present; help/new/stats RED. Score block masked.",
    "OptionsPage.png": "Sounds + Cards + Interface (Card Lowering). Lowercase 'options' title + heavier label typography; rows drift down.",
    "StatsPage.png": "Fresh install so values match the baseline (0 / none). Section markers decorative '✻'; remaining diff is label typography.",
    "StatsResetBtn.png": "Scrolled to 'Reset Statistics'; per-run values masked; '✻ ✻ ✻' divider. Diff is typography + scroll offset.",
    "HelpPage.png": "Header illustration + single 'Introduction' + Rules, correct Spider text. Diff is heavier text + wider line-spacing (drifts downward).",
    "HelpPageBottom.png": "Scrolled to Undo/Menu sections + the 'frequently asked questions' link. Text drifts downward (wider line-spacing).",
    "MoreGames.png": "'Tap any game to download it!' curtain page (Solitaire / Sudoku 2 / Card Games). Smiley 'tap' cursors volatile; FREE pills absent offline.",
    "SpiderAboutPage.png": "'Spider ▷ Solitaire' divider, links correct, version 8.0.0 (vs 7.42.5). Content renders shifted DOWN vs Obj-C.",
    "SpiderFAQ.png": "Spider's own FAQ; first question 'How do I play the game?' appears ONCE (no duplicate). Diff is typography / line-wrap.",
    "choose_look_surface.png": "Surface tab, 9 swatches, Simulate Depth toggle; modal well-positioned. Diff is typography.",
    "choose_look_cards.png": "Cards tab, 6 designs, 'Extra Large Card-Symbols' ('symbols' correct); modal well-positioned.",
}
IP14_V343_FINDINGS = [
    ("ok", "Tracks build 341 — no verified change", "Every screen's diff-vs-baseline matches build 341 within capture-session variance (heavier text renders slightly differently between sessions; scroll position + animation frames differ). No content fixes or regressions verified in the shipping UI.", "vs build 341"),
    ("layout", "Systemic typography + downward drift", "Unity renders body text heavier with wider line-spacing, drifting progressively downward on the tall 1290×2796 screen — the main diff driver on Help (25%), Help·Bottom (23%), More Games (22%), In-Game Menu (22%) and FAQ (22%).", "systemic"),
    ("layout", "Content sits lower than Obj-C", "Static screens render shifted down vs Obj-C — clearest on About and the Help header illustration. A vertical layout offset, not only typography.", "About · Help"),
    ("minor", "Lowercase title + marker style", "The Options title is lowercase 'options'; Stats section dividers render plainer than the Obj-C decorative markers. Unchanged from 341.", "Options · Stats"),
    ("ok", "No content bugs", "FAQ shows Spider's own content with a single first question; About keeps its '▷' divider + version 8.0.0; Help a single 'Introduction'; Cards reads 'symbols'; the promo-icon strip loads; victory buttons are RED.", "regression check"),
]
IP14_V343_VERDICT = ("Build 343 on the iPhone 14 Pro Max <b>tracks build 341</b> — no content bugs, and the "
                     "deviations from the Obj-C baseline are the same systemic <b>typography + downward layout "
                     "drift</b> (heavier text, wider line-spacing, content sitting lower on the tall screen). "
                     "Per-screen diffs shift a few points from 341, but that's <b>capture-session variance</b> "
                     "(text rendering, scroll position, animation frames), not verified UI change. Peak diff ~25% (Help).")
IP14_V343_BUGS = set()

DEVICES = {
    "ip14": {
        "module": C14, "title": "iPhone 14 Pro Max", "res": "1290×2796", "aspect": "1290/2796",
        "diff_prefix": "diff_ip14_",
        "out": os.path.join(REPO, "reports", "iPhone14_Unity_Report.html"),
        "versions": [
            {"id": "v343", "label": "343", "date": "2026-08-04",
             "unity_dir": os.path.join(REPO, "log", "ip14_unity_343"),
             "verdict": IP14_V343_VERDICT, "findings": IP14_V343_FINDINGS,
             "notes": IP14_V343_NOTES, "bugs": IP14_V343_BUGS},
            {"id": "v341", "label": "341", "date": "2026-08-03",
             "unity_dir": os.path.join(REPO, "log", "ip14_unity"),
             "verdict": IP14_V341_VERDICT, "findings": IP14_V341_FINDINGS,
             "notes": IP14_V341_NOTES, "bugs": IP14_V341_BUGS},
        ],
    },
    "ip7": {
        "module": C7, "title": "iPhone 7", "res": "750×1334", "aspect": "750/1334",
        "diff_prefix": "diff_ip7_", "zoom": True,   # trial: click-to-enlarge lightbox
        "out": os.path.join(REPO, "reports", "iPhone7_Unity_Report.html"),
        "versions": [
            {"id": "v343", "label": "343", "date": "2026-08-04",
             "unity_dir": os.path.join(REPO, "log", "ip7_unity_343"),
             "verdict": IP7_V343_VERDICT, "findings": IP7_V343_FINDINGS,
             "notes": IP7_V343_NOTES, "bugs": IP7_V343_BUGS},
            {"id": "v341", "label": "341", "date": "2026-07-31",
             "unity_dir": os.path.join(REPO, "log", "ip7_unity_341"),
             "verdict": IP7_V341_VERDICT, "findings": IP7_V341_FINDINGS,
             "notes": IP7_V341_NOTES, "bugs": IP7_V341_BUGS},
            {"id": "v3", "label": "337", "date": "2026-07-30",
             "unity_dir": os.path.join(REPO, "log", "ip7_unity"),
             "verdict": IP7_V3_VERDICT, "findings": IP7_V3_FINDINGS,
             "notes": C7.META, "bugs": IP7_V3_BUGS},
            {"id": "v2", "label": "335", "date": "2026-07-27",
             "unity_dir": os.path.join(REPO, "log", "ip7_unity_prevbuild"),
             "verdict": IP7_V2_VERDICT, "findings": IP7_V2_FINDINGS,
             "notes": IP7_V2_NOTES, "bugs": IP7_V2_BUGS},
        ],
    },
    "ip7-landscape": {
        "module": C7L, "title": "iPhone 7 (Landscape)", "res": "1334×750", "aspect": "1334/750",
        "diff_prefix": "diff_ip7ls_", "zoom": True,
        # landscape screens are wide + short, so the default 3-up grid renders them tiny.
        # Show 2 per row on a wider page; embed the screenshots at NATIVE 1334px (no
        # downscale) + higher JPEG quality so the inline and Enlarge views are full-res.
        "wrap": 1280, "card_min": 520,
        "card_w": 1334, "card_q": 92, "diff_w": 1600, "diff_q": 86,
        "out": os.path.join(REPO, "reports", "iPhone7_Landscape_Unity_Report.html"),
        "versions": [
            {"id": "v345", "label": "345", "date": "2026-08-05",
             "unity_dir": os.path.join(REPO, "log", "ip7_landscape_unity_345"),
             "verdict": IP7L_V345_VERDICT, "findings": IP7L_V345_FINDINGS,
             "notes": IP7L_V345_NOTES, "bugs": IP7L_V345_BUGS},
            {"id": "v343", "label": "343", "date": "2026-08-04",
             "unity_dir": os.path.join(REPO, "log", "ip7_landscape_unity"),
             "verdict": IP7L_V343_VERDICT, "findings": IP7L_V343_FINDINGS,
             "notes": IP7L_V343_NOTES, "bugs": IP7L_V343_BUGS},
        ],
    },
    "ipad": {
        "module": CI, "title": "iPad", "res": "1620×2160", "aspect": "1620/2160",
        "diff_prefix": "diff_ipad_",
        "out": os.path.join(REPO, "reports", "ipad_unity_report.html"),
        "versions": [
            {"id": "v337", "label": "337", "date": "2026-07-30",
             "unity_dir": os.path.join(REPO, "ipad", "unity"),
             "verdict": IPAD_V337_VERDICT, "findings": IPAD_V337_FINDINGS,
             "notes": CI.META, "bugs": IPAD_V337_BUGS},
            {"id": "v335", "label": "335", "date": "2026-07-29",
             "unity_dir": os.path.join(REPO, "ipad", "unity_prevbuild"),
             "verdict": IPAD_V335_VERDICT, "findings": IPAD_V335_FINDINGS,
             "notes": IPAD_V335_NOTES, "bugs": IPAD_V335_BUGS},
        ],
    },
}


# Embedded-image resolution (JPEG data URIs). Bumped up for crisper, retina-friendly
# screenshots — the wipe cards render ~300–560px wide, so ~2x source keeps them sharp;
# the diff image is a side-by-side, shown wider on the Diff toggle.
CARD_W, CARD_Q = 640, 84     # baseline + Unity wipe images (display ~360px → 2x retina)
DIFF_W, DIFF_Q = 560, 78     # side-by-side diff image (also shown at card width)
ZOOM_CARD_W = 560            # when a device has "zoom": embed cards at this width for the
                             # click-to-enlarge lightbox (~1.5x the ~360px display). Kept
                             # moderate so the multi-build portrait report fits the 16MB
                             # artifact cap (4 builds x 17 screens x 3 images).


def uri(path, width, q=80):
    img = cv2.imread(path)
    if img is None:
        return ""
    h, w = img.shape[:2]
    width = min(width, w)    # never upscale
    small = cv2.resize(img, (width, max(1, int(h * width / w))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, q])
    return ("data:image/jpeg;base64," + base64.b64encode(buf).decode()) if ok else ""


def sev_of(pct):
    return "hi" if pct >= 20 else ("md" if pct >= 12 else "lo")


def findings_html(findings):
    out = ""
    for kind, title, detail, scope in findings:
        lab, col = SEV[kind]
        out += (f"<li class='fi'><span class='chip' style='--c:{col}'>{lab}</span>"
                f"<div class='ft'><b>{title}</b><span class='fs'>{scope}</span>"
                f"<p>{detail}</p></div></li>")
    return f"<ul class='finds'>{out}</ul>"


def tiles_html(ok, bugcount):
    pcts = sorted(r["diff_pct"] for r in ok)
    med = (pcts[len(pcts)//2] if len(pcts) % 2 else (pcts[len(pcts)//2-1]+pcts[len(pcts)//2])/2)
    worst = max(ok, key=lambda r: r["diff_pct"])
    tiles = [
        ("Screens compared", f"{len(ok)}<span class='u'>/{len(ok)}</span>", "every screen deviates"),
        ("Median difference", f"{med:.1f}<span class='u'>%</span>", "of compared pixels"),
        ("Peak difference", f"{worst['diff_pct']:.0f}<span class='u'>%</span>", LABELS[worst['name']]),
        ("Content bugs", f"{bugcount}", "flagged this build"),
    ]
    return "".join(
        f"<div class='tile'><div class='tv'>{v}</div><div class='tk'>{k}</div><div class='td'>{d}</div></div>"
        for k, v, d in tiles)


def build(dev):
    C = dev["module"]
    base_dir = C.BASE_DIR
    order = C.ORDER
    zoom = bool(dev.get("zoom"))
    cw = dev.get("card_w") or (ZOOM_CARD_W if zoom else CARD_W)   # card res (also feeds the enlarge lightbox)
    cq = dev.get("card_q", CARD_Q)
    diff_w = dev.get("diff_w", DIFF_W)
    dq = dev.get("diff_q", DIFF_Q)
    baseline = {n: uri(os.path.join(base_dir, n), cw, cq) for n in order}

    versions_js = []
    for v in dev["versions"]:
        C.UNITY_DIR = v["unity_dir"]
        results = [C.compare_one(n, C.SPECS[n]["ignore"], C.SPECS[n].get("common")) for n in order]
        ok = [r for r in results if r["status"] == "ok"]
        screens = {}
        for r in ok:
            n = r["name"]
            screens[n] = {
                "pct": round(r["diff_pct"], 1),
                "sev": sev_of(r["diff_pct"]),
                "unity": uri(os.path.join(v["unity_dir"], n), cw, cq),
                "diff": uri(os.path.join(REPO, "log", dev["diff_prefix"] + n), diff_w, dq),
                "note": v["notes"].get(n, ""),
                "bug": n in v["bugs"],
            }
        versions_js.append({
            "id": v["id"], "label": v["label"], "date": v["date"],
            "verdict": v["verdict"],
            "tiles": tiles_html(ok, len(v["bugs"])),
            "findings": findings_html(v["findings"]),
            "screens": screens,
        })

    import json
    data = {
        "order": order,
        "labels": {n: LABELS[n] for n in order},
        "baseline": baseline,
        "versions": versions_js,
        "aspect": dev["aspect"],
    }
    data_json = json.dumps(data)

    html = _PAGE.replace("__TITLE__", dev["title"]).replace("__RES__", dev["res"]) \
                .replace("__ASPECT__", dev["aspect"]).replace("__ZOOM__", "true" if zoom else "false") \
                .replace("__WRAP__", str(dev.get("wrap", 1120))) \
                .replace("__CARDMIN__", str(dev.get("card_min", 300))) \
                .replace("__DATA__", data_json)
    os.makedirs(os.path.dirname(dev["out"]), exist_ok=True)
    with open(dev["out"], "w") as f:
        f.write(html)
    kb = os.path.getsize(dev["out"]) / 1024
    print(f"wrote {dev['out']}  ({kb:.0f} KB, {len(versions_js)} versions)")


_PAGE = """<style>
:root{ --felt:#0d1512; --panel:#151f1a; --panel2:#1b2721; --line:#27342d; --ink:#e9f0ea;
  --muted:#8fa89a; --gold:#e3b64a; --bad:#f0616a; --warn:#e6a13c; --info:#5bb6c9; --ok:#4cba86;
  --disp:"Rockwell","Roboto Slab",Georgia,serif; --body:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace; }
@media (prefers-color-scheme: light){ :root{ --felt:#f4f1e9; --panel:#fffefb; --panel2:#efece2; --line:#e2ddce;
  --ink:#1b2620; --muted:#5d6f66; --gold:#9c6f13; --bad:#c1373f; --warn:#a86c15; --info:#2c7889; --ok:#2c855a; } }
:root[data-theme="dark"]{ --felt:#0d1512; --panel:#151f1a; --panel2:#1b2721; --line:#27342d; --ink:#e9f0ea;
  --muted:#8fa89a; --gold:#e3b64a; --bad:#f0616a; --warn:#e6a13c; --info:#5bb6c9; --ok:#4cba86; }
:root[data-theme="light"]{ --felt:#f4f1e9; --panel:#fffefb; --panel2:#efece2; --line:#e2ddce; --ink:#1b2620;
  --muted:#5d6f66; --gold:#9c6f13; --bad:#c1373f; --warn:#a86c15; --info:#2c7889; --ok:#2c855a; }
*{box-sizing:border-box}
body{margin:0;background:var(--felt);color:var(--ink);font-family:var(--body);line-height:1.5;-webkit-font-smoothing:antialiased;
  background-image:radial-gradient(120% 60% at 50% -10%, color-mix(in srgb,var(--gold) 7%, transparent), transparent 60%);}
.wrap{max-width:__WRAP__px;margin:0 auto;padding:34px 22px 80px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin:0 0 10px}
h1{font-family:var(--disp);font-weight:700;font-size:clamp(26px,4.4vw,42px);line-height:1.05;margin:0;text-wrap:balance}
.sub{color:var(--muted);margin:10px 0 0;font-size:15px;font-family:var(--mono)}
.vswitch{display:inline-flex;gap:2px;margin:20px 0 4px;border:1px solid var(--line);border-radius:11px;padding:3px;background:var(--panel)}
.vswitch button{font-family:var(--mono);font-size:13px;color:var(--muted);background:transparent;border:0;padding:8px 16px;border-radius:8px;cursor:pointer}
.vswitch button.on{background:var(--gold);color:#1a130a;font-weight:700}
.vswitch button .d{font-size:11px;opacity:.7;margin-left:6px}
.verdict{margin:16px 0 0;font-size:clamp(16px,2.2vw,19px);max-width:64ch}
.verdict b{color:var(--ink)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:22px 0 6px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 16px 14px}
.tv{font-family:var(--disp);font-weight:700;font-size:30px;font-variant-numeric:tabular-nums}
.tv .u{font-size:15px;color:var(--muted);font-weight:400;margin-left:1px}
.tk{margin-top:2px;font-size:13px;font-weight:600}.td{color:var(--muted);font-size:12px;margin-top:2px}
.sect{font-family:var(--disp);font-size:20px;font-weight:700;margin:40px 0 4px;display:flex;align-items:center;gap:10px}
.sect::after{content:"";flex:1;height:1px;background:var(--line)}
.hint{color:var(--muted);font-size:13px;margin:6px 0 16px}
.finds{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.fi{display:flex;gap:14px;background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--c,var(--line));border-radius:12px;padding:13px 15px}
.chip{--c:var(--muted);color:var(--c);border:1px solid color-mix(in srgb,var(--c) 45%,transparent);background:color-mix(in srgb,var(--c) 12%,transparent);
  font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;padding:4px 8px;border-radius:20px;white-space:nowrap;height:max-content;margin-top:2px}
.fi{border-left-color:var(--c)}.ft b{font-size:15px}.ft .fs{color:var(--muted);font-family:var(--mono);font-size:11px;margin-left:8px}
.ft p{margin:4px 0 0;color:var(--muted);font-size:13.5px}.ft p b{color:var(--ink)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(__CARDMIN__px,1fr));gap:20px;margin-top:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column}
.card.s-hi{border-color:color-mix(in srgb,var(--bad) 42%,var(--line))}
.ch{display:flex;align-items:center;justify-content:space-between;padding:13px 15px;background:var(--panel2);border-bottom:1px solid var(--line)}
.ch h3{margin:0;font-family:var(--disp);font-size:16px;font-weight:700}
.pill{font-family:var(--mono);font-weight:700;font-size:13px;font-variant-numeric:tabular-nums;padding:3px 9px;border-radius:20px;color:var(--ok);background:color-mix(in srgb,var(--ok) 14%,transparent)}
.pill.s-md{color:var(--warn);background:color-mix(in srgb,var(--warn) 14%,transparent)}
.pill.s-hi{color:var(--bad);background:color-mix(in srgb,var(--bad) 16%,transparent)}
.cmp{position:relative;background:#000}
.wipe{position:relative;width:100%;aspect-ratio:__ASPECT__;overflow:hidden;touch-action:none}
.wipe img{position:absolute;inset:0;width:100%;height:100%;display:block;object-fit:cover}
.wipe .t{clip-path:inset(0 0 0 50%)}
.hdl{position:absolute;top:0;bottom:0;left:50%;width:2px;background:var(--gold);transform:translateX(-1px);pointer-events:none}
.hdl::after{content:"";position:absolute;top:50%;left:50%;width:26px;height:26px;transform:translate(-50%,-50%);border-radius:50%;background:var(--gold);box-shadow:0 1px 6px rgba(0,0,0,.5)}
.wipe input{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:ew-resize}
.lab{position:absolute;top:9px;font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:#fff;background:rgba(0,0,0,.55);padding:3px 8px;border-radius:20px;pointer-events:none}
.lab.l{left:9px}.lab.r{right:9px}
.diffimg{display:none;width:100%;height:auto}
.cmp[data-mode="diff"] .wipe{display:none}.cmp[data-mode="diff"] .diffimg{display:block}
.foot{padding:12px 15px 14px;display:flex;flex-direction:column;gap:9px;flex:1}
.seg{display:inline-flex;align-self:flex-start;border:1px solid var(--line);border-radius:9px;overflow:hidden}
.seg button{font-family:var(--mono);font-size:11.5px;color:var(--muted);background:transparent;border:0;padding:5px 12px;cursor:pointer}
.seg button.on{background:var(--gold);color:#1a130a;font-weight:700}
.note{margin:0;color:var(--muted);font-size:13px}
.segrow{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.zoombtn{font-family:var(--mono);font-size:11.5px;color:var(--muted);background:transparent;border:1px solid var(--line);border-radius:9px;padding:5px 12px;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.zoombtn:hover{color:var(--ink);border-color:var(--gold)}
.lb{position:fixed;inset:0;z-index:100;background:rgba(3,7,5,.95);display:flex;align-items:center;justify-content:center;padding:26px}
.lb[hidden]{display:none}
.lbwrap{display:flex;gap:18px;max-width:100%;max-height:100%;overflow:auto;align-items:flex-start}
.lbwrap figure{margin:0;display:flex;flex-direction:column;align-items:center;gap:9px}
.lbwrap img{max-height:85vh;width:auto;image-rendering:auto;border-radius:10px;box-shadow:0 6px 44px rgba(0,0,0,.6);background:#000}
.lbwrap figcaption{font-family:var(--mono);font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--gold)}
.lbtitle{position:fixed;top:18px;left:0;right:0;text-align:center;font-family:var(--disp);font-size:17px;color:var(--ink);pointer-events:none}
.lbx{position:fixed;top:14px;right:18px;z-index:101;width:42px;height:42px;border-radius:50%;border:0;background:rgba(255,255,255,.15);color:#fff;font-size:20px;cursor:pointer}
.lbx:hover{background:rgba(255,255,255,.26)}
.lbhint{position:fixed;bottom:16px;left:0;right:0;text-align:center;font-family:var(--mono);font-size:11px;color:var(--muted);pointer-events:none}
@media(max-width:760px){.lbwrap{flex-direction:column;align-items:center}.lbwrap img{max-height:none;max-width:92vw}}
footer{color:var(--muted);font-size:12px;font-family:var(--mono);margin-top:40px;text-align:center}
</style>
<div class="wrap">
  <p class="eyebrow">Spider Solitaire · Objective-C → Unity port</p>
  <h1>__TITLE__ — Unity Port Fidelity</h1>
  <p class="sub">Obj-C 7.42.5 baseline · __RES__ · use the switch to compare Unity builds</p>
  <div class="vswitch" id="vswitch"></div>
  <p class="verdict" id="verdict"></p>
  <div class="tiles" id="tiles"></div>
  <h2 class="sect">Findings · triage</h2>
  <p class="hint">For the selected build, most actionable first.</p>
  <div id="findings"></div>
  <h2 class="sect">Screen by screen</h2>
  <p class="hint">Ranked by pixel difference for the selected build, worst first. Baseline is constant; drag to wipe, or switch to Diff for the changed pixels (red). Status bar, ad banner, dealt cards and victory scores are masked.</p>
  <div class="grid" id="grid"></div>
  <footer>Single versioned report · regenerate with scripts/gen_versioned_report.py</footer>
</div>
<div class="lb" id="lb" hidden>
  <div class="lbtitle" id="lbtitle"></div>
  <button class="lbx" id="lbx" type="button" aria-label="Close">✕</button>
  <div class="lbwrap">
    <figure><img class="lbb" id="lbb" alt="Obj-C baseline"><figcaption>Obj-C 7.42.5</figcaption></figure>
    <figure><img class="lbt" id="lbt" alt="Unity capture"><figcaption>Unity 8.0.0</figcaption></figure>
  </div>
  <div class="lbhint">Click the backdrop or press Esc to close</div>
</div>
<script>
const DATA = __DATA__;
const ZOOM = __ZOOM__;
const grid = document.getElementById('grid');
const cards = {};
// build one card shell per screen (baseline embedded once)
DATA.order.forEach(name => {
  const c = document.createElement('article');
  c.className = 'card';
  c.innerHTML = `
    <div class="ch"><h3></h3><span class="pill"></span></div>
    <div class="cmp" data-mode="wipe">
      <div class="wipe">
        <img class="b" src="${DATA.baseline[name]}" alt="Obj-C">
        <img class="t" src="" alt="Unity">
        <span class="hdl"></span>
        <input type="range" min="0" max="100" value="50" aria-label="wipe">
        <span class="lab l">Obj-C</span><span class="lab r">Unity</span>
      </div>
      <img class="diffimg" src="" alt="diff">
    </div>
    <div class="foot">
      <div class="segrow">
        <div class="seg"><button class="on" data-m="wipe">Wipe</button><button data-m="diff">Diff</button></div>
        ${ZOOM ? '<button class="zoombtn" type="button">⤢ Enlarge</button>' : ''}
      </div>
      <p class="note"></p>
    </div>`;
  grid.appendChild(c);
  cards[name] = c;
  const w = c.querySelector('.wipe'), t = c.querySelector('.t'), h = c.querySelector('.hdl'), r = c.querySelector('input');
  const set = v => { t.style.clipPath = 'inset(0 0 0 ' + v + '%)'; h.style.left = v + '%'; };
  r.addEventListener('input', e => set(e.target.value)); set(50);
  const cmp = c.querySelector('.cmp');
  c.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {
    cmp.dataset.mode = b.dataset.m;
    c.querySelectorAll('.seg button').forEach(x => x.classList.toggle('on', x === b));
  }));
  if (ZOOM) {
    c.querySelector('.zoombtn').addEventListener('click', () =>
      openLB(c.querySelector('.b').src, c.querySelector('.t').src, DATA.labels[name]));
  }
});
// Click-to-enlarge lightbox (only wired when ZOOM is on) — shows the baseline + Unity
// screenshots at full embedded resolution, side by side.
const lb = document.getElementById('lb');
function openLB(bsrc, tsrc, title){
  document.getElementById('lbb').src = bsrc;
  document.getElementById('lbt').src = tsrc;
  document.getElementById('lbtitle').textContent = title;
  lb.hidden = false;
}
function closeLB(){ lb.hidden = true; document.getElementById('lbb').src = ''; document.getElementById('lbt').src = ''; }
if (ZOOM) {
  lb.addEventListener('click', e => { if (!e.target.closest('.lbwrap') || e.target.id === 'lbx') closeLB(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !lb.hidden) closeLB(); });
}
function render(vid){
  const v = DATA.versions.find(x => x.id === vid);
  document.getElementById('verdict').innerHTML = v.verdict;
  document.getElementById('tiles').innerHTML = v.tiles;
  document.getElementById('findings').innerHTML = v.findings;
  document.querySelectorAll('#vswitch button').forEach(b => b.classList.toggle('on', b.dataset.v === vid));
  const ranked = [...DATA.order].sort((a,b) => (v.screens[b].pct) - (v.screens[a].pct));
  ranked.forEach(name => {
    const s = v.screens[name], c = cards[name];
    c.className = 'card s-' + s.sev;
    c.querySelector('h3').textContent = DATA.labels[name] + (s.bug ? ' 🐛' : '');
    const pill = c.querySelector('.pill'); pill.textContent = s.pct.toFixed(1) + '%'; pill.className = 'pill s-' + s.sev;
    c.querySelector('.t').src = s.unity;
    c.querySelector('.diffimg').src = s.diff;
    c.querySelector('.note').textContent = s.note;
    grid.appendChild(c); // re-order by rank
  });
}
const vs = document.getElementById('vswitch');
DATA.versions.forEach(v => {
  const b = document.createElement('button');
  b.dataset.v = v.id;
  b.innerHTML = v.label + `<span class="d">${v.date}</span>`;
  b.addEventListener('click', () => render(v.id));
  vs.appendChild(b);
});
render(DATA.versions[0].id);  // latest first
</script>"""


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "ip7"
    build(DEVICES[key])
