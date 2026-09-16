# CLAUDE.md

Guidance for Claude Code when working in this repo.

## What this is

Standalone iOS UI-automation for the **Spider Solitaire** game
(`com.fingerarts.Spider`, listed as "Spider" by FingerArts) using **Airtest**
(image recognition) + **Poco** (accessibility hierarchy) over **WebDriverAgent
(WDA)**. The **signed WDA build is committed here** at `wda/` — no signing and no
WDA build happen in this repo. It came originally from `../sudoku-automation`, which
is no longer needed. Setup for a new machine: `SETUP.md`.

Cloned from the sibling **`../solitaire-airtest`** project (regular Solitaire),
which shares FingerArts' menu chrome. The **`assets/` templates are inherited
from Solitaire** and still need re-verifying / re-cropping from a real Spider
Solitaire screenshot (`tests/launch_and_shoot.py`).

Drives a **real, wired iPhone** (not a simulator).

**Current focus — Obj-C → Unity port verification.** The game is being ported
from its Objective-C build to a **Unity** build. `baselines/` are screenshots of
the **Objective-C** build and are the **source of truth**; the app under test on
the device is the **Unity** build (v8.0.0+). The job is to catch where Unity
deviates from the Obj-C UI pixel-for-pixel — so a large baseline diff is the
intended *finding*, **not** a reason to re-baseline. The Unity build renders its
whole UI into an opaque view with **no accessibility tree** (Poco sees nothing),
and its buttons no longer match the inherited templates, so `tests/compare_unity.py`
drives it by fixed screen **coordinates**. The functional suite (`tests/verify*.py`
+ `run_all.py`) has been **converted to the Unity build** — the Obj-C build is no
longer functionally tested — and drives it by templates cropped from Unity's own
rendering (`unity_ui.py` + `assets_unity/`). See `tests/README.md`.

## Layout

| Path | Purpose |
|---|---|
| `config.py` | Game identity (`GAME_NAME`, `BUNDLE_ID`) + WDA URL / device URI. Env-overridable. |
| `helpers.py` | `launch_app()` (WDA session launch), `wda_status()`, the Airplane-Mode/Wi-Fi radio control (`set_network`, `network_state`), and the live device/app identity readers `os_version()` / `device_model()` / `app_info()` that `submitFeedback` asserts the feedback subject against. |
| `flows.py` | **The Obj-C driver** — launch/connect + template navigation, ~30 helpers against the `assets/` crops. No longer used by the `verify*.py` suite (that was converted to `unity_ui.py`); its live callers are `tests/compare_unity.py` and `scripts/capture_unity_screens.py`. This, plus `assets/`, is what Obj-C functional testing would be rebuilt on. |
| `driver.py` | **Dormant — imported by nothing.** A build-aware dispatcher meant to run one test against BOTH builds, resolving each action per build (`PROFILES`) after classifying the installed app with `detect_build()` — a WDA accessibility-tree probe, since Unity's tree is opaque and UIKit's is not (`BUILD=objc｜unity` overrides it). Never finished: wired for the menu + Options only. **Kept deliberately** — deleting it costs no coverage today, but `detect_build()` is the piece worth having back if the Obj-C build returns. Do not mistake it for the Obj-C driver; that is `flows.py`. |
| `visual.py` | Baseline (visual-regression) comparison: **masked exact-pixel** diff of `log/` captures vs `baselines/`, per-screen `max_diff` in `SPECS`. Not SSIM — that was too tolerant and missed shifts (see the Visual regression section below). |
| `unity_ui.py` | **Unity functional driver.** Drives the Unity build by templates cropped from *Unity's own* rendering (`assets_unity/`), not by blind coordinates and not with the Obj-C `assets/` (which don't match Unity). Navigation, the two look-alike Yes/No dialogs, game-table controls, the Options screen's toggles + sliders (`opt_*`), and pixel-observation helpers. Used by the `tests/verify*.py` suite. |
| `scripts/setup.sh` | Create `.venv`, install `requirements.txt`. |
| `scripts/wda.sh` | Launch + port-forward WDA. Resolves the build as `WDA_PRODUCTS` → in-repo `wda/` → `../sudoku-automation` fallback. |
| `wda/` | **The committed, signed WebDriverAgent build** (25 MB). Installs only on the 9 UDIDs in its profile; expires ~2027-07-02. `wda/README.md` has the device list and the rebuild route. Marked `binary` in `.gitattributes` so the code signature survives a clone. |
| `SETUP.md` | Start-to-finish setup for a new Mac + which screenshots must be captured before a comparison means anything. |
| `scripts/update_baselines.py` | Promote the latest `log/` screenshots to `baselines/`. |
| `tests/connect_check.py` | Smoke test: connect + screenshot. |
| `tests/launch_and_shoot.py` | Launch the game + screenshot (start of real flows). |
| `tests/verify*.py`, `tests/openDebugTools.py`, `tests/resetStats.py` | **Unity functional test cases** (first-launch T&C / Privacy links, main menu, play, difficulties, gameplay, options, stats, help, Helpshift offline redirect then online PeopleFun Support, more games, logo/about, choose look, promo icons + their App Store links, QA entry point, victory). Each runs standalone and drives `unity_ui.py`. `verifyFirstLaunch` walks both policy links only when the one-time card is up, then presses Home, enables Airplane Mode, turns Wi-Fi off, force-relaunches Spider, and leaves the suite on the menu. |
| `tests/verifyAds.py` | **Ad coverage — ONLINE only, not in `run_all.py`. Chunks 1-3 of a rebuild around the Dev Panel's "Max Debugger".** Brings the device online itself (`ui.online()`), opens the Dev Panel (unlocking it if needed — `open_dev_panel()` expands from the current screen once unlocked, including the table), and opens **MAX's Mediation Debugger**, which is native UIKit over the Unity view and so is asserted on its TITLE read from the accessibility tree. Its table is big enough that enumerating elements by class times out, so lookups use predicate queries (`ui._ax_first`). Then scrolls to the debugger's **Ads** section. The row reads **Select Live Network** when empty and changes to **Live Network** when a choice is persisted, so the test searches for either label; it selects **AppLovin** only when needed and confirms the picker checkmark. Closes those overlays, resumes or deals a game, waits ~30s, taps back, and walks the interstitial chain (StoreKit X, then the ad's own X) back onto the **game table**. If back does not show the ad, it fires on the next resume or new deal — that is expected. **Ends on the table on purpose**, so a re-run must not `launch_to_menu()` from there (that fires another interstitial and `to_menu()` answers with a cold launch that re-locks the Dev Panel). Two debugger traps: rows scrolled out of view keep UNTAPPABLE rects, so scrolling waits on `visible`, not presence; and "AppLovin" also appears under *Completed SDK Integrations*, so the window is confirmed by its NAVIGATION BAR before the name is looked up. The skip glyph is never tapped. Banner-era findings stay in the docstring. |
| `tests/triggerAdPoints.py` | **Interstitial trigger/cooldown coverage — ONLINE only, not in `run_all.py`.** Verifies the original five table/Victory rules plus global cooldown after a Help ad, long-table Back, short main-menu entry (Resume does not fire an ad), and long-table FAQ. Entry ads are valid cooldown-expiry events and are closed before the table clock starts; one inherited-cooldown ad on the first Options attempt gets one clean retry. The shared closer always handles StoreKit X before the ad's own X, saving `log/ad_unmatched.png` before an unmatched-X failure. `--part cooldown`, `--part victory`, `--part menu`, and `--part destinations` run the groups independently. Never cold-launches. |
| `tests/visitLastScore.py` | **Last Score — ONLINE only, not in `run_all.py`.** The difficulty picker's "LAST SCORE" opens the "Last Won Game Score" ranking view; its forward arrow cycles the period (4 taps = a full round trip); "leaderboards" and "achievements" each open Apple's Game Center sheet and close again. The first tap of either can raise a Game Center notice card instead of the sheet — OK it, then tap the same link again. Game Center needs the network + a signed-in Apple account. |
| `tests/verifyAdFreeVersion.py` | **Ad-free link — ONLINE only, not in `run_all.py`.** About's "ad free version" does **not** redirect straight out: it raises a No/Yes card ("Tap Yes to proceed to the App Store"), and only **Yes** hands off — to **Spider Solitaire +**, this game's paid build, asserted by name. Asserted on the foreground bundle id (`ui.left_app()`), never on pixels. Comes back the way a PERSON does — tapping the `◀ Spider` crumb iOS draws in the status bar (`ui.tap_back_to_app()`), not a programmatic resume — and must land on **About**, which is the proof the app was resumed rather than restarted. |
| `tests/submitFeedback.py` | **Feedback mail — standalone, not in `run_all.py`** (needs a Mail account). About's "submit feedback" raises a Cancel / **Write Email** alert, which opens **Mail** (`com.apple.mobilemail`) with a draft. The **subject** — `Spider 8.0.0 feedback (iPhone12,1, iOS 26.5 al/al) us` — is READ from Mail's accessibility tree and must name the game, version, model and iOS version, each derived live (`helpers.os_version` / `device_model` / `app_info`), never hardcoded. **Never sends**; deletes the draft from a `finally`. |
| `tests/verifyRelaunch.py` | **App-restore check — in `run_all.py` before `openDebugTools`.** Gets a game (resuming a paused one rather than dealing over it), plays one move, **presses Home, kills the app on the game screen**, and launches it again after ~3.5s and after ~35s. Both times it must come back on the game screen with **the same board** — matched by correlation (`ui.board_score`), *not* per-pixel. The Home press is load-bearing: the app writes its state on backgrounding, so a foreground kill brings back the **menu** instead. Before the QA unlock so the kill cannot hide the Dev Panel. |
| `tests/verifyChooseLook.py` | **Look/theme check — standalone, not in `run_all.py`.** Switches the Surface/Cards tabs, selects the **6th Surface palette** and the **5th Cards palette**, then opens a game and proves both reached the **game table**: the felt and the card backs are matched on *normalised* colour against the palette tapped in that same run (never a fixed felt value — this test is what repaints it). **Restores the default look** from a `finally`, because the menu's icon controls (`more_games`/`choose_look`/`menu_logo`) bake the felt into their crops and fall to 0.62-0.69 on a repainted surface. |
| `tests/run_all.py` | Run the whole **Unity** functional suite with a preflight (templates, WDA, `DEVICE_UDID`); print a PASS/FAIL summary that labels known Unity port gaps. Full doc: `tests/README.md`. |
| `scripts/capture_unity_screens.py` | Bootstrap capture: walk Unity by coordinate, screenshot every screen into `log/unity_screens/` (the input the templates are cut from). |
| `scripts/crop_unity_assets.py` | Cut Unity anchors out of those captures (`--device iphone14｜iphone11`). |
| `scripts/derive_unity_assets.py` | Derive one device's Unity templates from another's by multi-scale matching (ip14 → ip11 lands at scale ~0.64). |
| `scripts/verify_unity_assets.py` | Offline quality gate for the Unity templates: **fragile** (doesn't match another build's capture of the same screen) and **ambiguous** (matches a screen it shouldn't). No device needed. |
| `tests/compare_unity.py` | **Unity-port check:** coordinate-navigate the Unity build to all 10 baselined screens, capture + exact-pixel diff vs `baselines/` (Obj-C). `--report` also writes `log/unity_compare.html`. Captures its own screenshots, unlike the per-device tools. Exit code is 0 regardless of diff size — read the printed summary. |
| `tests/compare_unity_ip7.py` | **iPhone 7 portrait Unity-port check** (750×1334): diff `log/ip7_unity/` captures vs `iphone7/portrait/baselines/` with iPhone-7 masks + curated `META`. `--report` regenerates the versioned report `reports/iPhone7_Unity_Report.html` (build switcher). |
| `tests/compare_unity_ip7_landscape.py` | **iPhone 7 landscape Unity-port check** (1334×750): diff `log/ip7_landscape_unity/` captures vs `iphone7/landscape/baselines/` with landscape masks (re-measured for 1334×750, *not* rotated from portrait — Spider's landscape UI is a genuine reflow, not a rotation) + curated `META`. Covers 17 screens. `--report` regenerates the versioned report `reports/iPhone7_Landscape_Unity_Report.html` (build switcher). |
| `tests/compare_unity_ipad.py` | **iPad Unity-port check** (1620×2160): diff `ipad/unity/` captures vs `ipad/baselines/` with iPad masks + curated `META`. `--report` regenerates the versioned report `reports/ipad_unity_report.html` (build switcher). |
| `tests/compare_unity_ip14.py` | **iPhone 14 Pro Max Unity-port check** (1290×2796): diff per-build captures (`log/ip14_unity/` = build 341, `log/ip14_unity_343/` = build 343) vs `iphone14/baselines/` with iPhone-14 masks (measured, not scaled — 19.5:9 reflows vs ip7's 16:9) + learned volatile masks (`iphone14/baselines/<name>.volatile.png`) + a `DEV_PANEL` mask over the build-343 "Dev Panel" debug button on both victory screens + curated `META`. Covers 17 screens (the ip7 set + `HelpPageBottom`). `--report` regenerates the versioned report `reports/iPhone14_Unity_Report.html` (build switcher 343 / 341). |
| `scripts/gen_compare_report.py` | Build the interactive wipe/fade comparison report (`log/unity_compare.html`) from the latest `log/` captures + `baselines/`. Curated per-element callouts live in its `META`. |
| `scripts/gen_versioned_report.py` | The **polished, Artifact-ready** fidelity report — a single page with a **build switcher** (e.g. 341 / 337 / 335) that swaps verdict, tiles, findings + all screen cards; the Obj-C baseline stays constant. `python scripts/gen_versioned_report.py {ip7\|ip7-landscape\|ipad\|ip14}` → `reports/<Device>_Unity_Report.html` (ip7 → `iPhone7_Unity_Report.html`, ip7-landscape → `iPhone7_Landscape_Unity_Report.html`, ip14 → `iPhone14_Unity_Report.html`, ipad → `ipad_unity_report.html`). Per-build capture dirs, curated findings + per-device image sizing (the landscape report embeds native-res 1334×750 screenshots, 2-up) live in its `DEVICES` config. |
| `assets/` | Template images for image matching, cropped from the **Obj-C** build (commit these). Do **not** use these against Unity — they don't match. |
| `assets_unity/` | Template images cropped from the **Unity** build's own rendering, for `unity_ui.py`. **One set for every 19.5:9 phone** (iPhone 11 / 14 Pro Max / 16 Pro) — unlike `assets/`, this is *not* per-device: `unity_ui.find()` rescales each crop by `device width / REF_WIDTH` at match time. `iphone14/assets_unity/` is now only a reference set. |
| `scripts/verify_unity_scaling.py` | Offline gate for that claim: drives the real `unity_ui.find()` against saved captures from each device, reporting MISSED (set doesn't cover the device) and GHOST (matches a screen it shouldn't). `--synthetic` adds resampled profiles for phones we have no captures of. |
| `baselines/` | Committed baseline screenshots for visual regression (compared each `run_all`). |
| `reports/` | Committed fidelity reports: the per-device build-switcher HTML (`<dev>_unity_report.html`), dated snapshots, and `CHANGELOG.md`. |
| `log/` | Screenshots / run logs + diff images (git-ignored). |

**Visual regression:** each test screenshots into `log/<name>.png`; `run_all.py`'s
baseline phase does an **exact-pixel** compare against `baselines/<name>.png`
(`visual.py`) and flags any pixel that differs beyond a tolerance — so
position/size/font/asset changes are caught (SSIM was too tolerant and missed
shifts). A screen fails when the fraction of compared pixels that differ exceeds
its `max_diff` (`visual.SPECS`); the diff `log/diff_<name>.png` shows the baseline
beside the capture with the differing pixels in red and boxed, masked areas dimmed.
Three exclusions keep it from firing on legitimate churn: (1) fixed chrome —
status bar, ad banner, this build's debug overlay/Test Banner (`COMMON_IGNORE`);
(2) per-screen `ignore` — e.g. the randomly-dealt card tableau, changing Stats
numbers; (3) a learned **volatile mask** `baselines/<name>.volatile.png` — pixels
that flicker between same-build captures (menu glow/sparkles). Build baselines +
masks with: `VIS_SHOTS=3 ./.venv/bin/python tests/run_all.py` then
`./.venv/bin/python scripts/update_baselines.py`. Without a volatile mask an
animated screen shows its animation as diffs (run_all flags `[no volatile mask]`).
`SKIP_VISUAL=1` skips the phase. Re-baseline (from a representative app state) after
an intended UI change or a new build.

## Running (order matters)

```bash
./scripts/setup.sh                             # one-time: build .venv
./scripts/wda.sh                               # start WDA (iPhone UNLOCKED); leave running
./.venv/bin/python tests/connect_check.py      # verify
./.venv/bin/python tests/launch_and_shoot.py   # launch Spider Solitaire + screenshot
./.venv/bin/python tests/run_all.py            # Obj-C suite (template-based; won't pass on Unity)
./.venv/bin/python tests/compare_unity.py --report   # Unity vs Obj-C pixel comparison + HTML report
./.venv/bin/python tests/run_all.py            # Unity FUNCTIONAL suite (does it work?)
```

Always use the project venv: `./.venv/bin/python`.

**Unity comparison run** (`tests/compare_unity.py`): navigates the Unity build by
coordinates to all ten baselined screens, captures into `log/`, exact-pixel diffs
each vs `baselines/`, prints a per-screen `diff%`/threshold summary, and writes
`log/diff_*.png`. `--report` regenerates `log/unity_compare.html` (drag-to-compare
wipe/fade viewer with alignment rulers + callout pins). If a new Unity build moves
elements, re-shoot with `tests/launch_and_shoot.py` and update the coordinates at
the top of `tests/compare_unity.py`.

## Unity functional testing (`tests/verify*.py` + `run_all.py`)

A **second axis**, alongside pixel fidelity (`compare_unity*.py`): does the
Unity build actually **work**? The `verify*.py` cases were **converted in
place** from Obj-C to Unity — the Obj-C build is no longer functionally tested.
Full doc: `tests/README.md`.

**13/13 on the iPhone 11, Unity build 353 (2026-08-13).** `KNOWN_UNITY_GAPS` is
now **empty** — no test is expected to fail. Note the build number comes from
`CFBundleVersion`; the marketing version reads `8.0.0` on every Unity build and
cannot tell them apart.

**Which game each promo icon opens is now asserted, not just "five different
pages".** The old check compared the five App Store captures pairwise and
failed only if two were identical — which a SWAP survives, since swapping two
links still leaves five different pages. It now reads the store page's NAME
from its accessibility tree (the App Store is ordinary UIKit, unlike the game)
and asserts two things: each page carries its icon's expected name, AND each
expected name matches exactly ONE of the five. The second half is the one that
catches a swap — three of the five titles contain "Solitaire" and two contain
"Card", so a looser keyword would pass on the wrong page. The store injects a
'▻' glyph INTO the title at a varying position ('▻ Solitaire: Classic Cards'
but 'Card ▻ Games'), so `ui.store_title()` strips it. Proved offline:
`tests/verifyMoreGamesIcons.py --selftest` shows the check failing on each swap.

**The promo icon strip is NOT a port gap** — this was wrong here for a while, in
two different ways ("Unity dropped it", then "build 353 regressed it"). The
strip only appears once **at least one game has been completed**; on a fresh
install with stats at 0 the app does not draw it. Hence `verifyMoreGamesIcons`
runs **last**, after `verifyVictory` wins a game — keep that order, and never
file a bug from a fresh-install capture (this also applies when capturing menus
for the pixel reports).

**The suite no longer restarts the app between tests.** `helpers.launch_app()`
attaches to the running app (`forceAppLaunch=False`); WDA's default had been
restarting it at every test start and discarding in-app state. That is what lets
`verifyVictory` reuse the Dev Panel `openDebugTools` unlocked instead of
repeating the gesture. Tests that need a genuinely fresh app ask for it:
`ui.launch_to_menu(force=True)` (openDebugTools) and `ui.cold_launch()`.

The hidden QA entry point (`openDebugTools`) **was** on that list and is not any
more — it survives the port: **5 rapid taps on the About screen's spider emblem**
reveal a bottom-right **"Dev Panel"** button. The earlier "opens nothing" reading
was a harness fault — the burst was aimed at `about_logo`, whose centre sits on
the *wordmark*, which is inert; the emblem ~50 px above works. Hence the separate
`about_emblem` crop. The gesture **toggles** (a second burst hides the button)
and only the *gesture* is tied to About — once unlocked the button appears on
every screen and stays until the app is relaunched.

**That button opens the QA cheats** — the Unity equivalent of the Obj-C build's
cheat. Tapping it expands a panel: surface / language / card-back pickers,
**Complete Game**, Max Debugger, Kill Banner Ad, PT Debugger, Screen Stats.
`unity_ui.win_game(level)` drives the whole thing (`open_dev_panel` →
`complete_game` → victory), which restores **synthetic-win coverage** and makes
the victory screens reachable without playing a game out. Three things about it:

- **Complete Game acts on the ACTIVE game.** Fired from About it does nothing
  (0.00% of the screen); the panel must be armed first and the cheat fired from
  the table.
- **The expanded panel is a persistent overlay** — it follows you across screens
  (which is what makes the above work) but covers the right-hand column where the
  main menu draws its labels, so `on_menu()`/`to_menu()` cannot confirm the menu
  while it is up. Navigate around it (About's top-left back, Play, Easy) or
  `close_dev_panel()` first.
- **A third dialog exists:** a "Did you know?" tip with **OK / Show Me** (not
  Yes/No) lands on the table after a deal and swallows taps until answered — it
  ate the first cheat attempt. `settle_prompts()` answers it OK first ("Show Me"
  navigates away to Options).
- **That tip is found by SHAPE, not by template — and its old crops were never
  once a match.** `prompt_tip` / `tip_ok` were cut from a rendering where the
  card was **dark green with white text**; this build draws it **pale mint with
  black text**, so the two are near photographic negatives. Measured on build
  363 against captures where the tip was plainly on screen, `prompt_tip` scored
  **0.344 and 0.397** against a 0.70 bar — `is_on("prompt_tip")` was always
  False and `settle_prompts()` never saw the tip at all, so it sat there eating
  the taps aimed at the table. That is what failed **2 of 4 levels** in
  `verifyDifficultyLevels` as "the cheat did not lead to the victory screen".
  The crops are **deleted**, not re-cut: the card is translucent (so any crop
  bakes in what sat behind it), and the tip ships in a **one-button and a
  two-button** form with different geometry. `ui.card_dialog()` finds it as a
  large solid bright rounded rect and `ui.card_buttons()` reads its pills, both
  relative to the picture's own colours, so a repainted surface changes nothing.
  The **reset-scores** prompt on Statistics is the same widget, and in both the
  **leftmost** button is the dismissing one (OK before "Show Me", No before Yes).
- **The Options page glides for over two seconds after a scroll**, and that made
  every slider read a lottery. `opt_row()` located the label in one capture and
  `opt_knob()` hunted the knob in the next; drift between the two was measured at
  **35 px** against a search band of only ±39 px. The bad case is not a miss —
  it catches *part* of the knob, reports a narrower one, and turns that into a
  plausible but **wrong number**. That is the whole of the "Card Lowering is a
  stepped slider that cannot reach mid-track" story: it is not stepped, and
  0.57 was a mis-measurement. `ui.opt_settled()` waits for the row to stop
  moving and hands back **the frame it measured in**, so the knob is read from
  that same frame; the value then repeats **exactly** (spread 0.0000).
- **A drag shorter than ~14 px (~0.06 of the track) does not register at all**
  — measured at swipe durations of 0.5 s, 1.2 s and 2.0 s alike, the knob moved
  by 0.000. So ~0.06 is the resolution a synthetic swipe *has* on these sliders,
  `slider_set()` answers a too-short correction by parking at the far end and
  re-approaching instead of re-issuing a gesture that cannot work, and
  `verifyOptions`' `MID_TOL` is **0.08**. Both ends still land exactly (0.00 /
  1.00), which is what the end-to-end assertions rest on.

**Why it locates by template, when `compare_unity.py` uses coordinates.** Both
choices are right for their job. A *pixel comparison* must not find its targets
using the pixels it is measuring — otherwise a regression that moves a button
would be silently followed instead of reported, hence fixed coordinates there.
A *functional* test has no such conflict: finding the button by sight is the
assertion. So `unity_ui.py` matches templates cropped from **Unity's own**
screenshots. That also fixed a real problem — `compare_unity.py`'s hardcoded
menu coordinates are ~15% off on the current build (the menu moved down), which
a template-based driver simply absorbs.

```bash
./scripts/wda.sh                                    # device UNLOCKED, leave running
./.venv/bin/python tests/run_all.py                 # whole suite (preflights first)
./.venv/bin/python tests/verifyGamePlay.py          # one case, standalone
```

Building/refreshing the templates for a new Unity build (this is **not**
re-baselining — `baselines/` stay Obj-C):

```bash
./.venv/bin/python scripts/capture_unity_screens.py            # log/unity_screens/
./.venv/bin/python scripts/crop_unity_assets.py --device iphone11
./.venv/bin/python scripts/verify_unity_assets.py              # gate before trusting
```

- **Template quality gate.** `verify_unity_assets.py` catches templates that are
  *fragile* (match their own source frame but not another build's capture of the
  same screen — the menu sparkle animation makes this a live risk) or *ambiguous*
  (match a screen they shouldn't). Runs offline. Currently 54/54 clean.
  **Three templates are NOT among the 54 and cannot be**, because the gate reads
  `iphone14/assets_unity/` and matches each crop against saved ip14 captures:
  `resume` (the picker's Resume ribbon is drawn only while a game is PAUSED, and
  `capture_unity_screens.py` never leaves it that way) and the `dev_*` crops
  (`dev_panel`, `dev_complete_game`, `dev_max_debugger`) — their only source
  frame is the iPhone-11 capture `log/unity_screens/SpiderAboutDevPanelOpen.png`,
  so they live in the shared set only and the ip14 build dirs have no Dev Panel
  capture to test them against. All were verified on the live device instead —
  `dev_max_debugger` matches at (708, 1321), one 64 px row below
  `dev_complete_game` at (708, 1257), and `tests/verifyAds.py` drives it.
- **Two findings from that gate are baked into the driver:** (1) the menu labels
  stay visible **behind the Choose Look modal**, so `ui.on_menu()` must rule the
  modal out rather than trust a matchable menu label; (2) the Help footer carries
  the same "frequently asked questions" link as About (real shared element).
- **Two look-alike dialogs, opposite answers:** abandon-paused-game → **Yes**,
  review-the-rules → **No**. Same geometry, so they're told apart by TEXT
  (`ui.settle_prompts()`), never by position — and the text is read over **WDA**,
  not matched as an image.
- **Never match an iOS alert as an image.** They're translucent, so a crop bakes
  in whatever sat behind the alert when it was cut. With the abandon prompt
  plainly on screen and its crops taken from that same device, `prompt_abandon`
  scored **0.188**, `dialog_yes` 0.311, `dialog_no` 0.329 — the templates were cut
  over the game table, that prompt sat over the difficulty picker. Every dealing
  test failed as "did not reach the game table". These are real
  `UIAlertController`s: `ui.alert_now()` reads the text, `ui.answer_dialog()`
  presses Yes/No by name, templates are only the fallback.
- **Two first-launch gates, normally Terms & Conditions, then ATT.** A separately
  reset tracking permission can put ATT first; `verifyFirstLaunch` clears only
  that prompt and waits for T&C so it does not accidentally skip the links. Both
  are **image-matched** — *neither* is visible to WDA. ATT is presented out of
  process (`/alert/text` 404s on it); the T&C pop-up is drawn by the app rather
  than presented as a `UIAlertController`, and measured on build 363 with a live
  session while it was plainly on screen, `/alert/text` returned `""` and
  `/alert/buttons` `[]`. This file used to claim T&C was matched by alert text —
  it was not, that branch never fired, and the gate was simply never dismissed.
  Nothing noticed because no test cold-launched until `verifyFirstLaunch` joined
  the suite. `ui.clear_overlays()` now taps `tc_continue` then **`att_allow`** —
  the app wants tracking *granted* before it lets a first launch through;
  answering "Ask App Not to Track" does not clear the gate. It still touches only
  alerts it positively recognises as gates.
- **The first-launch test follows both policy links before Continue.** Terms &
  Conditions and Privacy Policy must each open its own page and close back to
  the card. If the native **Accept All Cookies** button appears, the test taps
  it, waits until the banner is gone, and only then writes the full-page
  capture; the second page may inherit the cookie choice and show no banner.
  Their optional crops (`tc_terms_link` / `tc_terms_page` and
  `tc_privacy_link` / `tc_privacy_page`) are deliberately outside
  `run_all.REQUIRED`: normal launches do not show the card. A fresh card with
  missing crops saves `log/first_launch_terms_gate.png` and fails by name, but
  cleanup still accepts the gates and hands later tests an offline main menu.
  After accepting, `verifyFirstLaunch` presses Home before enabling Airplane
  Mode and turning Wi-Fi off, so the app has written the agreement state. It
  then force-relaunches Spider rather than resuming the existing process; the
  suite starts genuinely offline even if iOS remembered Wi-Fi as enabled.
- **`verifyHelpShift` is in `run_all` twice.** After Options it stays
  offline and only asserts Contact Us still leaves Options
  (`log/HelpShift.png`) — Helpshift will not render PeopleFun Support in
  Airplane Mode. Last, after `resetStats`, `verifyHelpShiftOnline` brings
  the device online and asserts the header **PeopleFun Support**. Going
  online any earlier lets ads interrupt the offline suite. It sits before
  `openDebugTools` on the offline half so a failed walk-back that
  cold-launches cannot hide the Dev Panel.
- **The gates come back far more often than "once per install".** The app writes
  its state when it goes to the **background**, and `cold_launch()` terminates it
  from the **foreground**, so the "agreed" flag can be lost and the pair
  reappears on the next launch. `cold_launch()` therefore sweeps, waits, and
  sweeps again — the gates arrive in sequence, so one immediate pass can clear
  T&C and return before ATT has been drawn.
- **`/alert/buttons` doesn't exist on this WDA (15.0.0) — it 404s.** That made
  `helpers.alert_buttons()` return `[]`, which `clear_overlays()` read as "no
  alert up", so the whole overlay sweep was dead code. `helpers.alert_text()` is
  the presence check; an empty button list means nothing either way.
- **A screenshot can't tell you which app you're looking at.** Use
  `ui.active_app()` for anything that hands off (the promo icons open the App
  Store), and `ui.resume()` to come back — it foregrounds Spider **without**
  restarting it, so in-app state survives. Never terminate to get back.
- **There are two ways back, and they test different things.** `ui.resume()`
  asks WDA to foreground the app; `ui.tap_back_to_app()` taps the `◀ Spider`
  crumb iOS draws in the status bar, which is what a *player* actually taps, so
  it is the one the hand-off tests use. **That crumb is BIDIRECTIONAL** — it
  names whichever app you came from, so from inside Spider it reads `◀ Mail`
  and tapping it throws the run back OUT (measured: `Spider →
  com.apple.mobilemail`). `tap_back_to_app()` therefore refuses to tap when the
  game is already in front.
- **Which screen you come back to depends on what you left to.** The App Store
  is an overlay Spider survives underneath, so `verifyAdFreeVersion` can demand
  it lands back on **About**. Mail is a whole second app, and coming back from it
  lands on the **main menu** — that is CONFIRMED EXPECTED, not a defect, so
  `submitFeedback` reports where it landed instead of demanding About.
- **No accessibility state to read**, so "did the control do anything?" is
  answered by comparing captures before/after. `test_gameplay` uses that for a
  genuine logic check: deal a row from the stock → the board must change → undo →
  the board must come back. Some feedback is **transient** — the hint highlight
  plays for <0.7s and the board then returns to *exactly* its previous pixels, so
  it must be sampled across the animation (`ui.peak_change_after`), not captured
  after a settle.
- **Run the suite OFFLINE (Airplane Mode) until `verifyMoreGamesIcons`, and start
  WDA *before* going offline.** Online, cross-promo interstitials interrupt
  screen transitions; opening Options
  from the in-game drawer was ad-interrupted on 3/3 attempts, and a blind tap on
  an interstitial can open a StoreKit App Store sheet over the app. `ui.lost()` +
  `ui.recover()` (terminate + relaunch — never hunt for the ad's close button)
  keep the suite from wedging, and the failure message names the ad rather than
  the button. **`tests/verifyMoreGamesIcons.py` is the deliberate in-suite
  network transition** — it needs live App Store pages to assert each promo
  destination's name, and leaves the remaining reset/support checks online.
  **`tests/verifyAds.py` and `tests/visitLastScore.py` remain standalone
  exceptions** — one needs ad traffic, the other needs Game Center, so neither
  is in `run_all.py`; run them on their own with the network up.
- **Ads themselves are now a tested axis, and they are hard to escape.** Measured
  on build 353: an interstitial fires on leaving a game (12/12 attempts) and
  renders *inside* the app; a video plays ~15s, then **opens an App Store product
  sheet by itself** (confirmed with screenshot-only sampling — 40 frames, no
  touch events); closing that sheet starts a further playable ad. Watched for a
  full **5 minutes** *without* pinning a network: only one closable control ever
  appeared (the sheet's X, at t+27s) and the app never came back on its own.
  Chunk 3 pins AppLovin first, then walks that chain on purpose: StoreKit X
  (`ui.tap_store_close`), then the ad's own X (`ui.tap_ad_close`), and asserts
  the **table** comes back. The "▶▶" skip glyph is deliberately **not** templated
  — its position moves between creatives and a crop scores 0.65–0.75 on real ads
  but **0.656 on the plain menu**. `ui.dismiss_ad()` was dead code on Unity (it
  looked for an `ad_close` crop that only exists in the Obj-C set); it now knows
  `ad_store_close` and `ui.ad_free(budget)` loops close-or-wait with a time limit.
  Another observed path: Back from a game can show an ad whose close returns to
  the main menu. Resume from that menu does not show another interstitial.

## Critical conventions / gotchas

- **Launch apps with `helpers.launch_app()`, NOT airtest's `start_app()`.**
  `start_app()` does not reliably foreground iOS apps on this device; the WDA
  session launch does. Launch first, `sleep(~3)`, then `connect_device()` and
  drive what's on screen.
- **When Airtest says `Failed to re-acquire session`, do not let it relaunch
  XCTest.** That recover path launches `SolitaireUITests.xctrunner` and fails.
  Use `ui.reconnect()` / `helpers.open_session()` against the already-running
  WDA from `scripts/wda.sh`. Snapshots and taps retry once on that error;
  `tap_back_to_app()` reconnects without foregrounding Spider first; `run_all.py`
  reconnects between tests (except after TestFlight). Never `recover()` to
  fix a dead session — that cold-launches and hides the Dev Panel.
- **WDA must be running** (via `scripts/wda.sh`) and the **iPhone unlocked** for
  anything to work. WDA listens on `http://127.0.0.1:8100`.
- **WDA + Airplane Mode don't mix on a restart.** iOS re-verifies the developer
  certificate over the network when the runner relaunches, so restarting
  `wda.sh` while the device is offline fails with *"The application could not be
  launched because the Developer App Certificate is not trusted"* — even if WDA
  was working minutes earlier on the same device (trust was simply still
  cached). Reconnect the device to the network (or re-trust under Settings →
  General → VPN & Device Management) and relaunch. Note this pulls against the
  offline preflight (`tests/preflight_offline.py`): go offline *after* WDA is up.
- **Pin the device with `DEVICE_UDID`.** Airtest picks the *first* device it can
  see, and that list includes **WiFi-paired** devices that aren't even plugged in
  — the iPhone 7 pairs over WiFi and sorts ahead of the USB-connected iPhone 11,
  so a run aimed at the 11 silently connected to the 7 (`wda xctest launched but
  check failed`). Aim both halves at the same phone:

  ```bash
  ./scripts/wda.sh 00008030-001C51DA0E80A02E              # WDA
  export DEVICE_UDID=00008030-001C51DA0E80A02E            # Airtest (config.py)
  ```

  `idevice_id -l` only lists USB devices, so it won't show the culprit —
  `tidevice list` does, with a `ConnType` column.
- **Airtest device URI:** `iOS:///http://127.0.0.1:8100` (see `config.DEVICE_URI`).
- **No new signing.** The signed WDA is committed at `wda/` and `wda.sh` finds it
  automatically. It only installs on the **9 UDIDs** baked into
  `embedded.mobileprovision` and expires **~2027-07-02** (signing cert, before the
  profile's 2027-08-12) — after that, or for an unlisted device, it must be rebuilt
  (`SETUP.md` → *Rebuilding WebDriverAgent*). `WDA_PRODUCTS=/path` points at another
  build without committing it.
- **Unity captures are not committed; Obj-C baselines are.** `log/` is git-ignored, so
  a fresh clone can run only the iPad comparison (its captures live in `ipad/unity/`).
  The per-device tools now exit **2** with an explanation when nothing was captured,
  instead of printing a clean summary of nothing.
- **Authoring:** Poco for stable-named menu buttons; image `Template(...)` for the
  card table where there are no accessibility IDs. Prefer `exists()` for
  assertions, `touch()` for taps. Crop templates from `log/*.png` into `assets/`.

## Environment facts

- Devices (real, wired — use one at a time; `idevice_id`/`wda.sh` auto-detect
  whichever is plugged in):
  - **iPhone 11** — Farooq's iPhone (`00008030-001C51DA0E80A02E`), iOS 26.5,
    **828×1792**. The default device: root `assets/` + `baselines/` (the latter the
    Obj-C source of truth for the Unity port).
  - **iPhone 7** "Kaala" (`385e82401ffb88ee946698f951ae9b991beba9da`), iOS
    **15.7.5**, **750×1334** (16:9). Its set is split by orientation under
    `iphone7/`: `iphone7/portrait/{assets,baselines}` (750×1334) and
    `iphone7/landscape/{assets,baselines}` (1334×750) — run with
    `DEVICE=iphone7/portrait` or `DEVICE=iphone7/landscape`. WDA is built for iOS
    26.5, so confirm the cert is trusted and WDA launches on iOS 15 before trusting
    a run (in practice the iPhone 7 uses tidevice capture, not WDA).
  - **iPhone 14 Pro Max** (`00008120-0001485A1E60201E`, `iPhone15,3`), iOS
    **26.5.2**, **1290×2796** (19.5:9). Its set is `iphone14/{assets,baselines}`
    (`DEVICE=iphone14`). Already in the default signed WDA profile, so plain
    `scripts/wda.sh` drives it (unlike the iPhone 7) — captured over WDA + Airtest.
    Per-build Unity captures land in `log/ip14_unity[_<build>]/` (e.g.
    `log/ip14_unity/` = 341, `log/ip14_unity_343/` = 343).
  - **iPhone 16 Pro** "Hamza's iPhone" (`00008140-0009492E1444801C`,
    `iPhone17,1`), iOS **26.5.2**, **1206×2622** (19.5:9), **@3x**. Runs the
    Unity functional suite with **no per-device templates** — `assets_unity/` is
    shared and rescaled at match time. Verified: **12/13**, the only failure the
    promo strip — which was later shown *not* to be a gap at all (that device had
    no completed game; see the functional-testing section). Real captures for the
    offline gate live in
    `log/ip16_real/`. Two one-time hurdles, both since cleared: it was not in the
    signed WDA profile (rebuild with `-allowProvisioningDeviceRegistration` took
    it from 4 to 9 devices), and it carried **another team's**
    WebDriverAgentRunner (`JSEM53HK74`), which iOS refuses to upgrade across
    teams — `xcrun devicectl device uninstall app --device <udid>
    com.facebook.WebDriverAgentRunner.xctrunner` first.
- **Per-device sets (`DEVICE`):** `DEVICE` is path-joined under the repo root, so
  `DEVICE=iphone7/portrait` points both image matching (`ASSETS`) and visual
  baselines (`BASELINES`) at `iphone7/portrait/{assets,baselines}` (and
  `iphone7/landscape` for landscape); `DEVICE=iphone14` → `iphone14/{assets,baselines}`
  (iPhone 14 Pro Max, 1290×2796 — the former root `assets_ip14/` set); unset = the
  iPhone 11 root `assets/` + `baselines/`. `visual.py`'s ignore-regions are
  828×1792-specific, so the per-device **comparison** runs through the dedicated
  `compare_unity_*` tools (which carry their own resolution masks), not `visual.py`.
  Never promote one device's / orientation's captures into another's baselines.
- Signing team: `4528523FZZ` (USERWISE SERVICES LLC); developer cert trusted on device.
- Tooling: Xcode 26.5, `iproxy` + `idevice_id` (libimobiledevice) on PATH.
- Find bundle IDs: `./.venv/bin/python -m tidevice applist`.

## Do not

- Commit `.venv/`, `log/`, or screenshots (already git-ignored).
- Add signing/provisioning logic here. `wda/` holds a *pre-signed* build; rebuilding
  it is a documented manual step (`SETUP.md`), not something this repo automates.
- **Re-baseline `baselines/` to the Unity build** during the port. They are the
  Obj-C source of truth; overwriting them with Unity captures destroys the
  reference and hides the very deviations the comparison exists to catch. When
  `compare_unity.py` shows diffs, the fix is navigation (coordinates) or a real
  port change — never the baselines.
