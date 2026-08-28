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
| `helpers.py` | `launch_app()` (WDA session launch) and `wda_status()`. |
| `flows.py` | Shared driver: launch/connect + template navigation helpers used by the tests. |
| `visual.py` | Baseline (visual-regression) comparison: masked SSIM of `log/` captures vs `baselines/`. |
| `unity_ui.py` | **Unity functional driver.** Drives the Unity build by templates cropped from *Unity's own* rendering (`assets_unity/`), not by blind coordinates and not with the Obj-C `assets/` (which don't match Unity). Navigation, the two look-alike Yes/No dialogs, game-table controls, the Options screen's toggles + sliders (`opt_*`), and pixel-observation helpers. Used by the `tests/verify*.py` suite. |
| `scripts/setup.sh` | Create `.venv`, install `requirements.txt`. |
| `scripts/wda.sh` | Launch + port-forward WDA. Resolves the build as `WDA_PRODUCTS` → in-repo `wda/` → `../sudoku-automation` fallback. |
| `wda/` | **The committed, signed WebDriverAgent build** (25 MB). Installs only on the 9 UDIDs in its profile; expires ~2027-07-02. `wda/README.md` has the device list and the rebuild route. Marked `binary` in `.gitattributes` so the code signature survives a clone. |
| `SETUP.md` | Start-to-finish setup for a new Mac + which screenshots must be captured before a comparison means anything. |
| `scripts/update_baselines.py` | Promote the latest `log/` screenshots to `baselines/`. |
| `tests/connect_check.py` | Smoke test: connect + screenshot. |
| `tests/launch_and_shoot.py` | Launch the game + screenshot (start of real flows). |
| `tests/verify*.py`, `tests/openDebugTools.py`, `tests/resetStats.py` | **Unity functional test cases** (main menu, play, difficulties, gameplay, options, stats, help, more games, logo/about, choose look, promo icons + their App Store links, QA entry point, victory). Each runs standalone and drives `unity_ui.py`. |
| `tests/verifyAds.py` | **Ad coverage — ONLINE only, not in `run_all.py`.** Banner is served, an interstitial fires on leaving a game, the ad never carries the user out of the app, and the app recovers. See `tests/README.md` → *Ads*. |
| `tests/visitLastScore.py` | **Last Score — ONLINE only, not in `run_all.py`.** The difficulty picker's "LAST SCORE" opens the "Last Won Game Score" ranking view; its forward arrow cycles the period (4 taps = a full round trip); "leaderboards" and "achievements" each open Apple's Game Center sheet and close again. Game Center needs the network + a signed-in Apple account. |
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
  ate the first cheat attempt. `settle_prompts()` now answers it OK first ("Show
  Me" navigates away to Options).

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
  (match a screen they shouldn't). Runs offline. Currently 53/53 clean.
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
- **Two first-launch gates, once per install — and every TestFlight build is a
  fresh install.** ATT prompt, then Terms & Conditions on the next launch. They
  need different mechanisms: ATT is presented **out of process** and is invisible
  to WDA (`/alert/text` 404s on it while the app's own alerts read back fine), so
  it's image-matched (`att_prompt` / `att_deny`); T&C is app-presented, so it's
  matched by alert text. `ui.clear_overlays()` handles both and touches only
  alerts it positively recognises as gates.
- **`/alert/buttons` doesn't exist on this WDA (15.0.0) — it 404s.** That made
  `helpers.alert_buttons()` return `[]`, which `clear_overlays()` read as "no
  alert up", so the whole overlay sweep was dead code. `helpers.alert_text()` is
  the presence check; an empty button list means nothing either way.
- **A screenshot can't tell you which app you're looking at.** Use
  `ui.active_app()` for anything that hands off (the promo icons open the App
  Store), and `ui.resume()` to come back — it foregrounds Spider **without**
  restarting it, so in-app state survives. Never terminate to get back.
- **No accessibility state to read**, so "did the control do anything?" is
  answered by comparing captures before/after. `test_gameplay` uses that for a
  genuine logic check: deal a row from the stock → the board must change → undo →
  the board must come back. Some feedback is **transient** — the hint highlight
  plays for <0.7s and the board then returns to *exactly* its previous pixels, so
  it must be sampled across the animation (`ui.peak_change_after`), not captured
  after a settle.
- **Run the suite OFFLINE (Airplane Mode), and start WDA *before* going offline.**
  Online, cross-promo interstitials interrupt screen transitions; opening Options
  from the in-game drawer was ad-interrupted on 3/3 attempts, and a blind tap on
  an interstitial can open a StoreKit App Store sheet over the app. `ui.lost()` +
  `ui.recover()` (terminate + relaunch — never hunt for the ad's close button)
  keep the suite from wedging, and the failure message names the ad rather than
  the button. **`tests/verifyAds.py` and `tests/visitLastScore.py` are the deliberate
  exceptions** — one needs ad traffic, the other needs Game Center, so neither
  is in `run_all.py`; run them on their own with the network up.
- **Ads themselves are now a tested axis, and they are hard to escape.** Measured
  on build 353: an interstitial fires on leaving a game (12/12 attempts) and
  renders *inside* the app; a video plays ~15s, then **opens an App Store product
  sheet by itself** (confirmed with screenshot-only sampling — 40 frames, no
  touch events); closing that sheet starts a further playable ad. Watched for a
  full **5 minutes**: only one closable control ever appeared (the sheet's X, at
  t+27s) and the app never came back on its own. The "▶▶" skip glyph is
  deliberately **not** templated — its position moves between creatives and a crop
  scores 0.65–0.75 on real ads but **0.656 on the plain menu**. `ui.dismiss_ad()`
  was dead code on Unity (it looked for an `ad_close` crop that only exists in the
  Obj-C set); it now knows `ad_store_close` and `ui.ad_free(budget)` loops
  close-or-wait with a time limit.

## Critical conventions / gotchas

- **Launch apps with `helpers.launch_app()`, NOT airtest's `start_app()`.**
  `start_app()` does not reliably foreground iOS apps on this device; the WDA
  session launch does. Launch first, `sleep(~3)`, then `connect_device()` and
  drive what's on screen.
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
