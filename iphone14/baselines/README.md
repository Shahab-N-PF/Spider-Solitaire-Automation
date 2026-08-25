# iphone14/baselines/

Visual-regression baselines for the **iPhone 14 Pro Max** (1290×2796), kept
**separate** from the repo-root `baselines/` (iPhone 11 / Objective-C — the
Unity-port source of truth). Selected by `DEVICE=iphone14` (→ `config.BASELINES`).

## Captured set (2026-07-31)

**17 screens** of the **Obj-C Spider build 7.42.5**, all 1290×2796:

- The 16 that match the fuller iPhone 7 set: `MainMenu`, `DifficultyLevels`,
  `Play`, `InGameMenu`, `VictoryScreen1`, `VictoryScreen2`, `OptionsPage`,
  `StatsPage`, `StatsResetBtn`, `HelpPage`, `MoreGames`, `SpiderAboutPage`,
  `SpiderFAQ`, `choose_look_surface`, `choose_look_cards`, `more_games_icons`.
- Plus `HelpPageBottom` — Help scrolled to the bottom (Undo/Menu sections + the
  FAQ link); a new screen not (yet) in the other devices' sets.

**How they were captured:** unlike the iPhone 7, this device runs WDA under Xcode
26.5, so the normal WDA/airtest flow works — `scripts/wda.sh 00008120-0001485A1E60201E`
(plug in **only** the iPhone 14 Pro Max) + `helpers.launch_app()` + Airtest
`snapshot()`. Manually-assisted: a human navigated to each screen and it was
grabbed once settled. Device in **Airplane Mode** for most screens.

**State notes (so re-captures match):**
- `MainMenu` / `more_games_icons` — both are the settled menu *with* the left
  cross-promo icon strip. That strip + the bottom ad banner load a beat after the
  menu (only appeared here after playing a game / visiting More Games), so an
  early capture misses them — re-shoot once the strip is up.
- `MoreGames` — captured **offline**, so the green **FREE** StoreKit price pills
  are absent (the iPhone 7 baseline has them); the smiley "tap" cursors are
  animated (volatile — will want a `.volatile.png` mask).
- `Play` / `InGameMenu` — the dealt tableau behind them is random (masked in
  comparison).
- Victory screens show run-dependent score/time/moves (masked).

## Before these can be COMPARED

`visual.py`'s dimensions + ignore-regions are iPhone-11 828×1792 coordinates, so
`DEVICE=iphone14` visual comparison is **not meaningful until** 1290×2796 region
values are added (status bar, bottom ad banner, game-table cards, stats numbers),
plus `<name>.volatile.png` masks for the animated menu screens.

## Rules
- Do **not** copy these into the root `baselines/`, and never promote
  root/iPhone-11 (or iPhone 7 / iPad) captures in here — each device's set is
  independent.
- Never re-baseline to the Unity build; the Obj-C captures are the reference the
  Unity port is checked against.
