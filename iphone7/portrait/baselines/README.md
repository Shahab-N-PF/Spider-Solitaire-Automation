# iphone7/portrait/baselines/

Portrait Obj-C **Spider 7.42.5** visual-regression baselines for the **iPhone 7**
(750×1334), kept **separate** from the repo-root `baselines/` (iPhone 11) and from
the landscape set at `../../landscape/baselines/`. The Unity-port diff tool
`tests/compare_unity_ip7.py` reads these directly (`BASE_DIR`); the legacy functional
suite reaches them via `DEVICE=iphone7/portrait` (→ `config.BASELINES`).

## Captured set

17 screens of the **Obj-C Spider build 7.42.5**, all 750×1334: `MainMenu`,
`DifficultyLevels`, `Play`, `InGameMenu`, `VictoryScreen1`, `VictoryScreen2`,
`LastScore`, `OptionsPage`, `StatsPage`, `StatsResetBtn`, `HelpPage`, `MoreGames`,
`SpiderAboutPage`, `SpiderFAQ`, `choose_look_surface`, `choose_look_cards`,
`more_games_icons`.

`LastScore` is the "Last Won Game Score" ranking view reached from the menu — it is
stamped with the **current date** ("Week of &lt;date&gt;" + a "&lt;date&gt;"), so the
compare tool masks the date along with the "won N" line + the current/rank/best
table (they track the calendar and play history, not layout).

**How they were captured:** manually-assisted via **tidevice** (`launch` +
`screenshot`), NOT the WDA/airtest suite — WDA can't run on this device (iOS 15.7.5
under Xcode 26.5; see [`../../README.md`](../../README.md)). A human navigated to
each screen and each was grabbed with:

```bash
./.venv/bin/python -m tidevice -u <udid> \
    screenshot iphone7/portrait/baselines/<Name>.png
```

Device in Airplane Mode for the later screens (no live ads). `MainMenu` and
`more_games_icons` are both the settled main menu (matching the iPhone 11 set).

## Comparison

`tests/compare_unity_ip7.py` diffs `log/ip7_unity*/` (Unity) vs these with 750×1334
mask regions + learned volatile masks. (The legacy `visual.py`/`run_all.py` flow
still uses iPhone-11 828×1792 ignore-regions, so that path isn't meaningful for the
iPhone 7 — use the compare tool.)

## Rules
- Do **not** copy these into the root `baselines/` or the landscape set — each
  device/orientation set is independent.
- Re-capture with the tidevice `screenshot` method above; never re-baseline to Unity.
