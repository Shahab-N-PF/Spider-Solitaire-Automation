# iphone7/landscape/baselines/

Obj-C **Spider 7.42.5** landscape reference screenshots for the **iPhone 7**
(**1334×750**), the source of truth the Unity landscape port is checked against.
Selected by `tests/compare_unity_ip7_landscape.py` (`BASE_DIR`).

## Captured set

**17 screens captured** (Obj-C **Spider 7.42.5**, all 1334×750) — the full portrait
set, all of which exist in landscape as a genuine reflow (menu arc on the right, logo
left-of-center, wood frame along the bottom):

`MainMenu`, `DifficultyLevels`, `Play`, `InGameMenu`, `VictoryScreen1`,
`VictoryScreen2`, `LastScore`, `OptionsPage`, `StatsPage`, `StatsResetBtn`,
`HelpPage`, `MoreGames`, `SpiderAboutPage`, `SpiderFAQ`, `choose_look_surface`,
`choose_look_cards`, `more_games_icons`.

`LastScore` is the "Last Won Game Score" ranking view reached from the menu — it is
stamped with the **current date** ("Week of &lt;date&gt;" + a "&lt;date&gt;"), so the
compare tool masks the date along with the "won N" line + the current/rank/best
table (they track the calendar and play history, not layout).

**How they were captured:** manually-assisted via **tidevice** `screenshot` with the
phone rotated to landscape (see [`../README.md`](../README.md)). Important quirk:
tidevice returns the framebuffer in the device's **native portrait** orientation
(750×1334) even while the game renders landscape, so each capture is **rotated 90°
counter-clockwise** to a true upright **1334×750** before saving. Re-capture the same
way (rotate CCW = PIL `Image.ROTATE_90`); a raw un-rotated grab will be portrait-shaped
with sideways content.

`more_games_icons` and `MainMenu` are both the settled main menu (the former waits for
the left cross-promo icon strip to finish loading). Live bottom **ad banner** rotates
between captures (seen: "Card Games", "FreeCell", "Sudoku 2", "Solitaire") — it must be
masked at compare time.

## Comparison

`tests/compare_unity_ip7_landscape.py` diffs `log/ip7_landscape_unity/` (Unity) vs
these baselines with **1334×750** mask regions measured off these captures (the
portrait values do **not** carry over):

- **No status bar** — the game runs fullscreen in landscape (unlike portrait).
- **Bottom ad banner** `(0, 610, W, H)` — added only on the banner-bearing screens
  (MainMenu, more_games_icons, Play, InGameMenu, choose_look_*, Victory*); the
  settings/menu screens (Options/Help/FAQ/About/Stats) have content that reaches the
  bottom and are compared in full.
- **Play** — dealt tableau + foundation + source `(0,0,W,425)` and the
  waste/score/hint band `(255,498,1060,592)`.
- **Victory 1 & 2** — the "won N" line + the current/rank/best numeric table.
- **Stats / StatsResetBtn** — the two per-run value columns per visible section
  (the ✻ markers, labels, and Reset button stay compared).

Verified by self-compare (baseline vs baseline = 0.00% on all 16) + a mask
perturbation test. A learned volatile mask `<name>.volatile.png` (e.g. the menu
glow / difficulty smiley cursor) is applied automatically if present.

## Rules
- Never copy portrait captures in here or vice-versa (different layout).
- Re-capture with the tidevice method; never re-baseline to the Unity build.
