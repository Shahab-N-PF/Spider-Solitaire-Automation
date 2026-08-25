# assets/

Template images for Airtest's image recognition live here. Crop them from a
device screenshot (e.g. `log/launch.png`) — a button, an icon, a game cell —
and reference them in code:

```python
from airtest.core.api import touch
from airtest.core.cv import Template
touch(Template("assets/play_button.png"))
```

Keep crops tight and distinctive. Commit these images (they are the "map" of the
game); the `log/` screenshots are throwaway and git-ignored.

## Current templates (main menu)

**Inherited from the sibling Solitaire project** (`../solitaire-airtest`), where
they were cropped from an 828×1792 iPhone 11 screenshot. FingerArts games share
the same menu chrome, so these are a strong starting point — but they have **not
been verified against a real Spider Solitaire screenshot yet**. First live step:
run `tests/launch_and_shoot.py`, then re-crop any that don't match from
`log/launch.png`. Referenced by name from `flows.py`:

| File | What it anchors | Source |
|---|---|---|
| `menu_play.png` | Play button | inherited |
| `menu_stats.png` | Stats button | inherited |
| `menu_options.png` | Options button | inherited |
| `menu_help.png` | Help button | inherited |
| `menu_about.png` | About button | **real Spider screenshot** |
| `more_games.png` | "More Games" (left) | inherited |
| `choose_look.png` | "Choose Look" (left) | inherited |
| `menu_daily.png` | (unused) Daily button — **Spider has no Daily** | inherited |

There is intentionally no game-title template — the title text differs per game,
so the menu checks in `flows.py` key off the Play/Options labels instead. Add a
`title_spider.png` here if you want a title assertion.

> **Note:** Spider's main menu is Play / Stats / Options / Help / **About** —
> there is **no "Daily"** button (that's a regular-Solitaire item). `test_main_menu`
> now asserts `About`, not `Daily`. `menu_daily.png` is kept for reference only;
> it would false-positive-match on the Spider menu under Airtest's keypoint
> matcher (raw template correlation is only ~0.46), so do not assert it.

## Spider-specific templates (verified against real Spider screenshots)

Cropped from live 828×1792 iPhone 11 screenshots (`log/diag_*.png`, `log/test_*.png`).
Referenced by name from `flows.py`:

| File | What it anchors |
|---|---|
| `difficulty_easy.png` | "Easy" on the difficulty picker (Play opens this, not the table) |
| `confirm_yes.png` | "Yes" on the "abandon the currently paused game?" dialog |
| `in_game_menu.png` | in-game top-bar "menu" button — durable proof a game was dealt |
| `screen_options.png` | "Options" title header — proves the Options screen opened |
| `screen_stats.png` | "Statistics" title header — proves the Stats screen opened |
| `screen_help.png` | "Introduction" heading — proves the Help screen opened |
| `screen_more_games.png` | "Tap any game to download it!" — proves the in-app More Games page opened |
| `menu_logo.png` | the Spider emblem at the top of the menu — tappable; opens the About screen |
| `promo_solitaire.png` | home promo-strip icon: Solitaire (green, cards) |
| `promo_sudoku2.png` | home promo-strip icon: Sudoku 2 (brown, "S²") |
| `promo_cardgames.png` | home promo-strip icon: Card Games (brown, four suits) |
| `promo_freecell.png` | home promo-strip icon: FreeCell (blue, crown) |
| `promo_spiderette.png` | home promo-strip icon: Spiderette (orange, spider) |
| `screen_about.png` | "© PeopleFun, Inc." copyright line — proves the About screen opened (via the About button OR the logo) |
| `screen_surface.png` | "Simulate Depth" — the Choose Look window's Surface tab is showing |
| `screen_cards.png` | "Extra Large Card-Symbols" — the Choose Look window's Cards tab is showing |
| `look_surface_tab.png` | the "Surface" tab button inside the Choose Look window |
| `look_cards_tab.png` | the "Cards" tab button inside the Choose Look window |
| `look_close.png` | the × close button on the Choose Look window (note: cross-matches `ad_close`) |
| `back_bar.png` | "◄ back" on sub-screens (serif, red bar) |
| `back_game.png` | "◄ back" on the game table (monospace, green bar) |
| `ad_close.png` | "×" on the cross-promo interstitial ad that can pop when leaving the table |

Navigation between tests uses these back buttons (see `flows.back_to_menu()`)
instead of killing/relaunching the app: it walks up one screen at a time,
closing any interstitial ad in between. The app is launched exactly once per run
(bootstrap in `flows.launch_to_menu()`, only when it can't already walk back to
the menu). Note the two back buttons need separate templates because they use
different fonts and backgrounds.

An offline audit (template vs every captured screen) confirms each anchor matches
its own screen at ~1.000 and stays below the 0.70 threshold elsewhere. The one
borderline is `in_game_menu` vs the Help screen (~0.70, the generic word "menu"
vs serif body text); harmless because `IN_GAME` is only asserted in `test_play`,
which never visits Help.

### First-launch pop-ups (cropped from a real reinstall)

| File | What it anchors |
|---|---|
| `tc_accept.png` | "Continue" on the first-launch Terms & Conditions pop-up |
| `att_allow.png` | "Allow" on the App Tracking Transparency prompt |
| `att_notrack.png` | "Ask App Not to Track" (alternative to `att_allow`) |

`flows.dismiss_popups()` is the **generic pop-up handler** — it clears native
alerts and known launch pop-ups by tapping the **positive** option, and is called
automatically by `launch_to_menu()` on every launch (no-op when the screen is
clear; verified that `tc_accept`/`att_allow` don't match normal screens). It:
1. reads any WDA-visible system alert's buttons and taps the affirmative one via
   `helpers.positive_button` (Allow / OK / Yes / Continue …, never Don't Allow /
   Cancel / No / Ask App Not to Track);
2. taps `att_allow` / `tc_accept` by image for prompts WDA can't see (the App
   Tracking prompt is a system alert its `app.alerts` API misses);
3. dismisses a cross-promo interstitial (×).
`handle_first_launch()` just launches and loops `dismiss_popups()` to the menu.
Switch the ATT choice by pointing the handler at `att_notrack` instead of `att_allow`.

Still useful to add later: per-row anchors for gameplay (undo/hints/stock), an
`About`-screen body anchor, and difficulty anchors beyond Easy.
