# iPad baselines (Obj-C source of truth)

Obj-C **Spider 7.42.5** screenshots for the **iPad (9th gen, iOS 26.3.1)**, the
reference the Unity port is checked against. **15 screens captured at 1620×2160**
(portrait) via WDA + Airtest on 2026-07-29 — see `../README.md` for the WDA
capture setup (tidevice does not work on iOS 26).

Screens (same names as the other device sets so they pair up in comparison):
`MainMenu`, `DifficultyLevels`, `Play`, `InGameMenu`, `VictoryScreen1`,
`VictoryScreen2`, `OptionsPage`, `StatsPage`, `HelpPage`, `MoreGames`,
`SpiderAboutPage`, `SpiderFAQ`, `choose_look_surface`, `choose_look_cards`,
`more_games_icons`.

Notes on capture state:
- AssistiveTouch was **off** for all but the first `MoreGames` frame (recaptured
  clean). The two glowing smileys on `MoreGames` are genuine screen elements.
- `StatsPage` values reflect games played on the device (2 wins), not a fresh
  install — pair with a same-history Unity capture or mask the values.
- Bottom ad banners rotate (Solitaire / Card Games / FreeCell / Candy Crush /
  Merge Mansion across frames) and are masked in the comparison.

Never overwrite these with Unity captures — they are the Obj-C reference.
`visual.py` ignore-regions are iPhone-11 (828×1792) specific; the iPad needs its
own 1620×2160 region values before any masked pixel comparison is meaningful.
