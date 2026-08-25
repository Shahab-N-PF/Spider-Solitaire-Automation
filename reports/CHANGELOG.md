# Unity-port fidelity reports — changelog

Per-device record of each Unity build we compared against the Obj-C baselines,
newest first, with what each build **fixed** and **broke/introduced** vs the
prior one. The reports themselves are regenerable from the committed captures.

Build numbers (e.g. **335**, **337**) are the Unity build's own numbers and are
the **same across devices** — build 335 on iPhone 7 is the same Unity build as
335 on iPad. The iPhone 7 also has an earlier "first build" (empty FAQ) that
predates 335.

- **Reference (Obj-C):** `iphone7/portrait/baselines/`, `ipad/baselines/` (Spider 7.42.5).
- **Unity captures:** `log/ip7_unity/` (iPhone 7), `ipad/unity/` (iPad); the
  immediately-prior build is kept in the matching `*_prevbuild/`.
- **HTML snapshots:** `reports/<device>_v<N>_<date>.html` (regenerable).
- **Diff tools:** `tests/compare_unity_ip7.py`, `tests/compare_unity_ipad.py`.
- **Report generator:** `scripts/gen_versioned_report.py` (build-switcher report).

Convention going forward: each new build → snapshot the HTML into `reports/`,
add a section here, and republish the artifact with a version **label** so the
artifact's version picker keeps the history at one URL.

---

## Unity functional suite — 13/13 on build 353, and two corrections

**2026-08-13.** iPhone 11, Unity build **353** (`CFBundleVersion`; every Unity
build reports marketing version `8.0.0`, so it cannot distinguish them). All 13
tests run individually in suite order: **13/13**. `run_all.py`'s
`KNOWN_UNITY_GAPS` is now **empty** — nothing is expected to fail.

### Correction: the promo icon strip was never a port gap

This changelog, `tests/README.md` and the test itself all previously recorded
the home-screen promo icon strip as **dropped by the Unity port**. Mid-session
it was then recorded, equally wrongly, as a **build-353 regression**. Both are
withdrawn.

**The strip only appears once at least one game has been completed.** On a fresh
install with stats at 0 the app does not draw it. Measured on one device and
build with no reinstall in between:

| Time | State | Icons matched |
|---|---|---|
| 12:07 | fresh install, 0 wins | 0 of 5 (0.305–0.641) |
| 12:11 | after T&C, a relaunch, a 12s settle, More Games visited — still 0 wins | 0 of 5 (0.343–0.433) |
| 12:43 | after `verifyVictory` completed a game | 4 of 5 (0.867–0.924) |

How the wrong call was reached, since it is the reusable lesson: the empty strip
was checked against three alternatives and one of the checks was too weak. "Not
a data problem, because More Games loads its full promo curtain" does **not**
follow — the curtain and the menu strip are fed separately. A capture taken in a
state the feature depends on (here: any completed game) is worth more than three
indirect eliminations.

Consequence: `verifyMoreGamesIcons` now runs **last**, after `verifyVictory`
wins a game and so satisfies its precondition. Keep that order. The same applies
to capturing menu screens for the pixel reports — a fresh-install capture is
missing the strip and is not comparable to a baseline that has it.

The 5th icon was a second, unrelated problem: `promo_freecell` scored ~0.54
against a strip plainly on screen because **FreeCell's app icon was redesigned**
(dark blue square → lighter squircle with a sparkle). These are other
publishers' icons, so the test now accepts any known art variant
(`promo_freecell_alt.png`).

### New coverage

* **Promo icons are checked as links.** Each of the 5 is tapped, must hand off to
  `com.apple.AppStore`, and must return to the menu on switching back — via
  `ui.resume()`, which foregrounds Spider **without** killing it. The 5
  destinations must also differ; that comparison uses only the icon/title band,
  because these pages share a publisher layout (whole-page, two genuinely
  different games sat 3.55 apart; on the band the closest pair is 18.36).
* **Ads are now an axis (`tests/verifyAds.py`, online only).** Hard assertions:
  a banner is served, an interstitial fires on leaving a game, the ad never
  carries the user out of the app, the app recovers.

### Ad findings (build 353) — not a port regression, but a UX problem

Ads are being served correctly, so the port did not break them. The experience
is the issue:

* An interstitial fires on leaving a game — **12 of 12** attempts — and renders
  inside the app.
* A video plays ~15s, then at ~16s **opens an App Store product sheet by
  itself**, with no tap. Confirmed with screenshot-only sampling: 40 frames, one
  per second, no touch events of any kind.
* Closing that sheet starts a **further playable ad**. Watched for a full **5
  minutes**: exactly one closable control ever appeared (the sheet's X, at
  t+27s) and Spider's own UI never returned. A user has no relaunch button.
* The only other exit is a small **"▶▶" skip glyph**, deliberately not templated:
  its position moves between creatives and a crop of it scores 0.65–0.75 on real
  ads but **0.656 on the plain main menu**.

Worth raising with whoever owns the ad configuration.

### Harness fixes behind all of the above

* **The app is no longer restarted between tests.** `helpers.launch_app()` used
  WDA's default `forceAppLaunch`, restarting the app at every test start and
  discarding in-app state. It now attaches (`force=False`). `verifyVictory`
  therefore reuses the Dev Panel `openDebugTools` unlocked instead of repeating
  the gesture; `openDebugTools` asks for `launch_to_menu(force=True)` because its
  premise is a hidden button.
* **iOS alerts are no longer matched as images.** They are translucent, so a crop
  carries whatever was behind it. With the abandon prompt plainly on screen and
  its crops cut from that same device: `prompt_abandon` **0.188**, `dialog_yes`
  0.311, `dialog_no` 0.329 — because the crops were cut over the game table and
  that prompt sat over the difficulty picker. Every dealing test failed as "did
  not reach the game table". Now read and answered over WDA by text/button name.
* **Two first-launch gates were wedging the first run on every new build** (each
  TestFlight install re-arms them): the ATT prompt, then Terms & Conditions. ATT
  is presented out of process and is **invisible to WDA** (`/alert/text` 404s on
  it while the app's own alerts read fine), so it is image-matched; T&C is
  app-presented and matched by text.
* **`/alert/buttons` 404s on WDA 15.0.0**, so `helpers.alert_buttons()` always
  returned `[]` and `ui.clear_overlays()` — written precisely to clear these
  gates — was dead code. `helpers.alert_text()` is the presence check now.
* **`ui.dismiss_ad()` was also dead on Unity**: it only looked for an `ad_close`
  crop that exists in the Obj-C `assets/` set, while `have()` searches the Unity
  set. It now knows `ad_store_close`, and `ui.ad_free(budget)` loops
  close-or-wait.

---

## Unity functional suite — proven on a third device (iPhone 16 Pro)

**2026-08-12.** The one-set design was validated on a real **iPhone 16 Pro**
(1206×2622, @3x): **12/13**, the only failure the promo strip. No new templates
and no new coordinates were added for it.

> **Superseded 2026-08-13:** that promo-strip failure was not a port gap. The
> strip needs a completed game, and this device had none. See the newest entry.

Getting there surfaced **four real bugs**, three of which were latent on the
iPhone 11 and would have caused intermittent failures there — the new device only
made them deterministic:

1. **Two rendering regimes.** Spider's confirmation dialogs are *native iOS
   alerts*, not Unity content, so they scale by point density (@2x→@3x = 1.500)
   while Unity artwork scales by width ratio (1.4565). 3% apart —
   `prompt_abandon` peaked 0.962 @1.500 but 0.694 within the width sweep, so the
   abandon prompt was unrecognised, answered "No", and **every game-dealing test
   failed**. Fixed with a per-template basis (`NATIVE_UI`), not a wider sweep.
2. **A dialog-classification race.** `settle_prompts()` tested `prompt_abandon`
   single-shot and only *then* waited for a dialog, so a prompt still drawing fell
   through to the fallback and got answered No. Now it waits, then classifies.
3. **The table anchor was unusable.** `in_game_menu` is the top bar's "menu"
   word — shared chrome (Stats, Help, victory) sitting *on the felt*. On a real
   table with a non-default surface it scored **0.794**, below the **0.827** it
   reaches on screens that are not a table. No threshold separates that;
   `SCREENS["table"]` now anchors on `tap_undo` (0.979 in the same frame).
4. **Surface-dependent templates.** Same root cause, different victim: because
   `verifyChooseLook` changes the surface, "menu" measured **0.74–0.84 across
   runs on the same device and table** — which is why the drawer step passed
   standalone and failed in the suite. `menu_button_pos()` now falls back to
   mirroring `back` across the screen (measured: same y, within 10px of the
   mirrored x on both phones, target ~140px wide). `back` is artwork, not text on
   felt, and holds 0.97 on every surface.

The general rule, now in the code: **a template that includes felt is
surface-dependent**, and the app's own theming makes that a moving target. Prefer
artwork anchors, or derive the position from one.

Device notes: the 16 Pro was not in the signed WDA profile (rebuilt with
`-allowProvisioningDeviceRegistration`, 4 → 9 devices, iPhone 11 and 14 retained)
and carried **another team's** WebDriverAgentRunner, which iOS will not upgrade
across teams — uninstall first.

---

## Unity functional suite — one template set for every device

**2026-08-12.** The suite no longer keeps a Unity template set per phone. Unity
scales its whole UI by **width** across the 19.5:9 devices, so `unity_ui.find()`
now resizes each crop by `device width / REF_WIDTH` (828) before matching, and
`config.UNITY_ASSETS` points at a single `assets_unity/` regardless of `DEVICE`.
An iPhone 16 Pro needs **no new templates and no new coordinates** — everything
resolution-dependent in the functional path was already a fraction of
`screen_size()`, read from the device at runtime.

Measured before building it, by cross-matching every template between an
iPhone 11 (828) and an iPhone 14 Pro Max (1290) capture of the same screen:

| direction | result | best scale | predicted |
|---|---|---|---|
| 1290 → 828 | 49/49 ≥0.80, median **0.978** | 0.645 (sd 0.003) | 0.642 |
| 828 → 1290 | 53/53 ≥0.80, median **0.981** | 1.560 (sd 0.005) | 1.558 |

Scales cluster within ~0.5% of the pure width ratio — close enough to predict,
not close enough to trust blindly, so `find()` sweeps a narrow band around the
prediction, tries the predicted scale first, and exits early (common case: one
`matchTemplate`, as before).

`scripts/verify_unity_scaling.py` is the new gate, and it drives the **real**
`find()` against saved captures rather than reimplementing the matcher, reporting
device coverage and ambiguity separately: iPhone 11 **66/66**, iPhone 14
**51/51**, synthetic iPhone 16 Pro **51/51** — 0 missed and 0 ghosts on all
three. (The 51s judge fewer templates only because the remaining screens were
captured on the iPhone 11 alone.)

Extending its allowlist surfaced a latent bug in `verify_unity_assets.py`:
`SHARED` defined `about_help` **twice**, so the later, narrower entry silently
overrode the first. Fixed; that gate still reports 53/53 clean.

**The sweep width turned out to matter more than the scaling.** Each extra scale
is another chance for a *wrong* screen to cross the threshold. A first cut used
±3% and the top bar's "menu" word (`in_game_menu`) began matching the Stats and
Help pages, which it scores only 0.684 / 0.659 against at native scale. Measured
false matches across five weak screens: ±3% → 3, ±1% → 1, single scale → 0. The
sweep is now ±1% — still 2–3× the observed prediction error.

The one case that survived was a weak anchor, not a scaling artefact:
`in_game_menu` is **shared chrome**, present on the Stats page, the Help page and
the victory screen, so it now carries `THRESH["in_game_menu"] = 0.85` (true
matches 0.98–1.00, highest false 0.827). That incidentally fixes a **pre-existing
bug**: at the default 0.70 the anchor cleared on the victory screen (0.78–0.83),
so `at_table()` reported a game in progress immediately after a win.

Also removed `unity_ui.T()`. Handing a `Template` to airtest matches at exactly
one scale — the size it was cropped at — so any use of it would silently fail on
a device other than the one the crop came from. Every tap now goes through
`find()`.

Two limits stated rather than papered over: the iPhone 16 Pro profile is
**synthetic** (a resampled iPhone 14 capture), so it validates the scaling math
and not that device's actual rendering; and the **iPhone 7** (750×1334, 16:9) is
excluded — its UI reflows rather than scaling, so it keeps its own set.

---

## Unity functional suite (iPhone 11 · 828×1792 · WDA + Airtest)

**2026-08-11 — the functional suite is now Unity-only.** A **second axis** beside
pixel fidelity: does the Unity build *work*? The `tests/verify*.py` cases
were converted in place from Obj-C to Unity (doc: `tests/README.md`), driven by
the new `unity_ui.py`. The Obj-C build is no longer functionally tested.

One test is **expected to fail** — a real port regression, kept in the suite so
it stays visible and labelled `[known Unity gap]` by `run_all.py`:

- **`verifyMoreGamesIcons`** — the home-screen promo icon strip (Solitaire,
  Sudoku 2, Card Games, FreeCell, Spiderette) is **absent** on Unity; present in
  `baselines/more_games_icons.png`. Also missing from an ONLINE capture in which
  the ad banner *did* load, so it is not an offline artifact.

> **WITHDRAWN 2026-08-13.** This was wrong, and the reasoning above is the
> instructive part: "the ad banner loaded, so the network is fine, so the strip
> should be there" does not follow — the banner, the More Games curtain and the
> menu strip are fed separately. The strip needs **one completed game**; every
> capture behind this entry was taken with zero wins. See the newest entry.

**Correction (same day): `openDebugTools` is NOT a port gap.** It was reported
here as one — "the hidden QA entry point is gone, 0.00% of the screen changes" —
and that was wrong. The QA entry point survives the port: **5 rapid taps on the
About screen's spider emblem** reveal a **"Dev Panel"** button in the
bottom-right corner. (It carries the same label as the button the pixel reports
flag on the iPhone 14 victory screens, but whether it is the same control has not
been checked — there it is visible with no gesture, which is the concern.) The
taps had been aimed at the `about_logo` crop, whose centre
lands on the *"Spider SOLITAIRE" wordmark* — and the wordmark really is inert, so
every measurement was a truthful 0.00% of the wrong target. The emblem ~50 px
above responds every time, which is why `about_emblem` is now its own template.

What caught it: a **positive control**. Firing the same W3C burst at a control
known to be live (About's `back`) changed 63.2% and landed on the menu, proving
delivery worked and moving suspicion to the tap *location*. A negative result
about a gesture is only worth reporting once the delivery path is shown to work.

Two properties the test depends on, both verified on device: the gesture
**toggles** (a second 5-tap burst hides the button), and its state **resets on
cold relaunch** and is scoped to the About screen — so "hidden beforehand" is a
safe precondition and the test is re-runnable.

Still true, and still the reason the result means anything: a loop of ordinary
airtest taps runs at **~510 ms per tap** on this rig, so five span >2.5 s and no
rapid-tap gesture could fire. `ui.rapid_tap()` sends the burst as a single W3C
Actions request executed on-device (~70–120 ms/tap), and the test asserts it did
not fall back *before* it judges the app.

**And that button is the cheat route.** Tapping Dev Panel expands a QA panel —
surface / language / card-back pickers, **Complete Game**, Max Debugger, Kill
Banner Ad, PT Debugger, Screen Stats — so the Unity build *does* have the
synthetic win the Obj-C build had. Verified end to end: arm the panel, deal an
Easy game, tap Complete Game → the board changes 24% and the **victory screen**
appears (`won 1 ✛ 0 abandoned`, easy level, 0:15). `unity_ui.win_game(level)`
wraps it, and `screen_victory` is now cropped for the iPhone 11 (previously only
the iPhone 14 set had victory templates).

Three properties that the wrapper exists to encode:

- **Complete Game acts on the ACTIVE game** — fired from About it changes 0.00%.
- **The expanded panel is a persistent overlay.** It follows you across screens,
  which is what lets the cheat be armed on About and fired from the table; the
  cost is that it covers the right-hand column, so `on_menu()`/`to_menu()` cannot
  see the menu while it is up.
- **A third dialog turned up:** a "Did you know?" tip (**OK / Show Me**, not
  Yes/No) lands on the table after a deal and swallows taps until answered. It
  silently ate the first cheat attempt — the tap matched the template and hit the
  modal scrim. `settle_prompts()` now answers it OK first; "Show Me" would
  navigate away to Options.

Everything else passes, including gameplay assertions the Obj-C suite never had:

- **deal → undo round trip**: dealing from the stock changes 9.6% of the board;
  undo returns it with **0.00% residual** — undo restores state exactly.
- hint highlight fires at 2.6% of the board; all five difficulties deal; all six
  in-game drawer actions behave.

**Why templates, not coordinates.** `compare_unity*.py` drives Unity by fixed
coordinates on purpose — a pixel comparison must not locate targets using the
pixels it measures. A functional test has no such conflict, so this suite matches
templates cropped from Unity's *own* rendering, making "the control is on screen"
a real assertion. That also absorbed a problem the coordinate approach has:
`compare_unity.py`'s hardcoded menu coordinates are **~15% stale** against this
build (the menu moved down) — worth a separate cleanup.

Three things the run established that aren't obvious:

- **Ads make one path untestable online.** Opening Options from the in-game
  drawer was interrupted by a full-screen cross-promo interstitial on **3/3**
  attempts, and a blind tap on one opened a **StoreKit App Store sheet** over the
  app. Offline (Airplane Mode) it passes. Start WDA *before* going offline.
- **Some feedback is transient.** The hint highlight plays for <0.7 s and the
  board returns to *exactly* its previous pixels — a single capture after a
  settle reads as "the control did nothing". Sampled across the animation
  instead. An earlier version of this test reported a false Unity defect.
- **Airtest can drive the wrong phone.** It picks the first device it sees,
  including **WiFi-paired** ones that aren't plugged in (the iPhone 7 outranked
  the USB iPhone 11). `config.DEVICE_UDID` now pins it.

Template integrity is gated offline by `scripts/verify_unity_assets.py`
(*fragile* = doesn't match another build's capture of the same screen, which the
animated menu sparkle makes a live risk; *ambiguous* = matches a screen it
shouldn't). Currently 53/53 clean.

---

## iPhone 14 Pro Max (1290×2796 · WDA capture)

### Build 343 — 2026-08-04  *(latest)*
Report: `reports/iPhone14_Unity_Report.html` (build switcher 343 / 341) · captures `log/ip14_unity_343/` · 17 screens.
Peak diffs: Help 25% · Help·Bottom 23% · More Games 22% · In-Game Menu 22% · FAQ 22%.

**vs build 341: tracks 341, no verified change.** Every screen's diff-vs-baseline matches 341 within
capture-session variance (heavier text renders slightly differently between capture sessions; scroll
position + animation frames differ). The lower peak numbers vs 341 are that variance, **not** a verified
UI improvement. No content fixes, no regressions in the shipping UI. Same conclusion as iPhone 7 portrait 343.

**Still open (unchanged from 341, no content bugs):**
- Systemic **typography + downward drift** (heavier text, wider line-spacing) is the main diff driver on
  Help / Help·Bottom / More Games / In-Game Menu / FAQ.
- **Vertical layout offset**: content sits lower than Obj-C (clearest on About + the Help header illustration).
- Lowercase "options" title; Stats dividers plainer than the Obj-C decorative `✻`.

**Capture notes:** `MainMenu` shot pre-settle (left promo strip not yet loaded) and `more_games_icons` shot
settled (strip present) — kept as two distinct states. A development-only **"Dev Panel" button reappeared
on both victory screens** (absent in 341, confirmed against pixels); it is **masked** in the diff by request
(`DEV_PANEL` region in `compare_unity_ip14.py`), so it does not drive the numbers.

### Build 341 — 2026-08-03  *(first Unity build measured on this device)*
Report: `reports/iPhone14_Unity_Report.html` · captures `log/ip14_unity/` · 17 screens.
Peak diffs: Help 33% · More Games 26% · FAQ 25% · Help·Bottom 24% · Options 23% · In-Game Menu 22%.

**Content fixes (same as iPhone 7 build 341):**
- 🟢 FAQ no longer duplicates its first question.
- 🟢 "Dev Panel" debug button gone from both victory screens.
- Promo-icon strip present; victory buttons red; difficulty smiley cursor.

**New / still open (no content bugs — layout/typography only):**
- 🔴 Fidelity noticeably weaker than iPhone 7: every screen deviates **13–33%**.
- Body text renders **heavier + wider line-spacing**, drifting progressively downward
  on the tall screen — the main diff driver on Help/FAQ/More Games/Options.
- **Vertical layout offset**: content sits lower than Obj-C (clearest on About and the
  Help header illustration).
- Lowercase "options" title; Stats divider plain `*` vs decorative `✻`.

Note: banner ad already excluded by the mask (banner solid sits below the mask edge);
high diffs are genuine typography/layout drift, not a masking artifact.

---

## iPad (9th gen · 1620×2160 · WDA capture)

### Build 337 — 2026-07-30  *(latest)*
Snapshot: `reports/ipad_unity_337_2026-07-30.html` · Artifact: `14359f8f-65e9-4890-84b1-3f0e753aae1d`
Peak diffs: In-Game Menu 28% · Help 26% · FAQ 21% · Options 17% · Play 17%.

**Fixed vs build 335:**
- Choose-Look modal positioned correctly again (was shifted + enlarged; 27% → 12%).
- Main-menu cross-promo icon strip restored (was dropped).
- Difficulty smiley cursor restored; stray "More Games/Choose Look" entries gone.
- Victory buttons red again (were blue); Victory·Score no longer shows a promo strip.
- FAQ loads Spider's own content (was the wrong game's / Klondike text).

**New / still open:**
- 🔴 FAQ **duplicates its first question** ("How do I play the game?" appears twice).
- 🔴 **"Dev Panel" debug button** ships on the Victory·Best screen.
- Systemic typography drift (Help/Options/FAQ); lowercase "options" title.
- Dropped bottom ad banner on Game Table + In-Game Menu; In-Game Menu tray differs.

### Build 335 — 2026-07-29
Artifact: `b47f1c93-…` *(deleted)*. Peak diffs: Choose Look·Cards 31% · Surface 27% · Help 25%.

Findings: FAQ showed the **wrong game's content** (Klondike questions); heavy
**layout drift** — Choose-Look modal shifted + enlarged, in-game menu panel
repositioned; **dropped** cross-promo icon strip + ad banners; victory buttons
blue + Victory·Score gained a promo strip; lowercase "options" + added "Interface"
section; Difficulty added More Games/Choose Look and dropped the smiley cursor;
Stats markers `*` vs `✻`; systemic typography drift.

---

## iPhone 7 (750×1334 · tidevice capture)

### Build 343 — 2026-08-04  *(latest)*
Report: `reports/iPhone7_Unity_Report.html` (build switcher 343 / 341 / 337 / 335) · captures `log/ip7_unity_343/`.
Artifact: `665c9996-52ea-4fdd-95ff-04e7378293c7` (label "343 · 2026-08-04").
Peak diffs: FAQ 17% · Options 15% · Stats·Reset 14% · More Games 13% · Help 13% · Stats 13%.
Expanded to 17 screens (added `LastScore` — the "Last Won Game Score" ranking view).

**vs build 341: no change.** Portrait UI is effectively identical to 341 — every screen's
diff-vs-baseline matches within capture noise (mean |Δ| 0.8pp; the text screens within ~0.3pp;
FAQ 16.70% on both). The only larger deltas (MainMenu, Difficulty, Choose Look·Cards) are
animation/state (sparkle glow, smiley cursor, promo-icon load), not UI changes. **No fixes, no regressions.**

**Still open (unchanged from 341, no content bugs):**
- Lowercase "options" title; systemic typography / line-wrap drift (heavier text) is the main diff driver.
- Stats markers are the decorative **✻** — note they were *already* ✻ in build 341; an earlier
  changelog note that called them a plain `*` was inaccurate (that was the pre-335 / early-build state).

Net: portrait is unchanged from 341 (~17% peak, no content bugs). The movement in build 343 is all
on the **landscape** side.

### Build 341 — 2026-07-31
Report: `reports/iPhone7_Unity_Report.html` (build switcher 341 / 337 / 335) · captures `log/ip7_unity_341/`.
Peak diffs: FAQ 16% · Options 16% · Stats·Reset 15% · More Games 13% · Stats 13% · Help 13%.
Expanded to 16 screens (added `StatsResetBtn`).

**Fixed vs build 337:**
- 🟢 FAQ **no longer duplicates its first question** — content matches Obj-C.
- 🟢 **"Dev Panel" debug button removed** from both victory screens.
- Promo strip, red victory buttons, difficulty smiley cursor — all still holding.

**New / still open:**
- No content bugs remain. Systemic typography / line-wrap drift (Unity renders text
  heavier + wraps differently) is now the main diff driver across text screens.
- Lowercase "options" title; Stats/divider markers plain `*` vs Obj-C decorative `✻`;
  promo-icon art renders slightly differently; dropped bottom ad banner on Play.

Net: clear improvement — peak diff fell from ~27–28% (337) to ~16%, and both open 337
bugs are fixed.

### Build 337 — 2026-07-30
Snapshot: `reports/ip7_unity_337_2026-07-30.html` · Artifact: `fba9aae3-dfe7-400a-bd93-076fa2f6be7f` (label "337 · 2026-07-30")
Peak diffs: More Games 28% · Help 28% · FAQ 27% · Victory·Best 22% · Victory·Score 19%.

**Fixed vs build 335:**
- FAQ now loads Spider's own content (was the wrong game's / Klondike text).
- Main-menu cross-promo icon strip restored (loads a beat after the menu).
- Difficulty smiley cursor restored; stray "More Games/Choose Look" entries gone.
- Victory buttons red again (were blue); Victory·Score no longer shows a promo strip.

**New / still open:**
- 🔴 FAQ **duplicates its first question** ("How do I play the game?" appears twice).
- 🔴 **"Dev Panel" debug button** ships on both victory screens.
- Systemic typography drift (Help/Options/FAQ/More Games); lowercase "options" title.
- Dropped bottom ad banner on Game Table + In-Game Menu; Stats markers `*` vs `✻`.

### Build 335 — 2026-07-27
Snapshot: `reports/ip7_unity_335_2026-07-27.html` · Artifact: `144afc28-…`
Peak diffs: Help 33% · FAQ 30% · More Games 27%. (Expanded to 15 screens — added
In-Game Menu + the two Victory screens.)

**Fixed vs the first build:**
- Empty FAQ now populated.
- Duplicated Help "Introduction" removed.
- About title "▷" divider restored.
- Typos fixed: "feeback" → "feedback" (About), "syymbols" → "symbols" (Cards).

**New / still open:**
- 🔴 FAQ now shows the **wrong game's content** (Klondike questions, not Spider's).
- Cross-promo icon strip still dropped from the main menu.
- Victory buttons blue (Obj-C red); Victory·Score gained a promo-icon strip.
- Systemic typography drift.

### First build — 2026-07-27  *(pre-335)*
Artifacts: `90187146-…`, `f048bdd2-…`. 12 screens. Peak diffs: Help 29% · More Games 27% · Cards 25%.

Findings: **empty FAQ** (all Q&A blank); **duplicated** Help "Introduction";
typos "submit feeback" (About) and "syymbols" (Cards); **dropped** left promo-icon
strip + bottom ad banner (main menu); Stats markers `*` vs `✻`; Options trailing
period + added "Interface" section; Difficulty missing smiley cursor / "Last Score";
Play missing bottom ad banner; card-back grid reordered.

---

## iPhone 7 — Landscape (1334×750 · tidevice capture)

Landscape is a genuine reflow of the UI, not a rotation, so it has its own baselines
(`iphone7/landscape/baselines/`), masks, diff tool (`tests/compare_unity_ip7_landscape.py`)
and report. Captured via tidevice with the phone rotated, then rotated 90° CCW to a true
1334×750 (tidevice returns the native-portrait framebuffer).

### Build 345 — 2026-08-05  *(latest)*
Report: `reports/iPhone7_Landscape_345_Report.html` — a **standalone, single-build** report
(`scripts/gen_standalone_report.py`), **not** added to the versioned switcher report (which stays at 343).
Captures `log/ip7_landscape_unity_345/` · 17 screens.
Peak diffs (after the baseline/mask corrections below): Menu·Promo Icons 26% · Difficulty 25% · Victory 23/23% ·
Options 21% · Choose Look·Surface 21% · Main Menu 20%.

**Clean improvement over 343 — every screen better or level, no regressions** (apples-to-apples, current tool):
- 🟢 **In-game menu adapted to landscape** — the pause tray now uses the **3-column** landscape grid
  (replay/abandon/options · new/help/FAQ) instead of 343's portrait **2-column** layout. 47% → 16%, the
  biggest fix. Residual: button ordering within the grid differs slightly from Obj-C; bottom ad banner dropped (masked).
- 🟢 **Choose-Look modal + victory screens repositioned** much closer to Obj-C (Surface 37→21, Cards 35→18,
  Victory 39/38 → 23/23); Stats/FAQ/About/LastScore/Play/Help all down 6–15pp.
- Only Options ticked **up** ~3pp (18→21) — minor typography variance, not structural.

**Corrections made this run (why the numbers differ from the first pass):**
- 🔧 **MainMenu + DifficultyLevels Obj-C baselines were in a wrong state and were re-captured.** This alone
  resolved the apparent **DifficultyLevels "regression"** (first pass read 15%→30% and looked stable/real; against
  the corrected baseline it is **flat vs 343** at ~25%). Lesson: verified the finding against a re-captured
  baseline, not just prior numbers — the "regression" was a bad reference. Old baselines backed up in scratchpad.
- 🔧 **Volatile masks built for all 17 landscape screens** (`iphone7/landscape/baselines/*.volatile.png`) —
  9 animated (sparkle glow / smiley / leaderboard bubble), 8 static/empty. Learned from Obj-C for the two
  re-captured screens, from Unity 345 for the rest.
- 🔧 **DifficultyLevels ignore-list was missing `BOTTOM_BANNER`** that MainMenu has (both carry the ad banner) —
  added for consistency (28→25%).
- 🔧 **"Dev Panel" button masked** on both victory screens (`DEV_PANEL_LS` in `compare_unity_ip7_landscape.py`),
  by request — it still ships but no longer drives the diff.

**Systemic (remaining diff drivers, no content bugs):** Unity renders the felt slightly **redder** than Obj-C
(~+13 R) and body text heavier / re-wrapped; lowercase "options" title. FAQ single first question; ✻ markers;
promo strip present; victory buttons RED; About ▷ divider + version 8.0.0.

### Build 343 — 2026-08-04  *(first landscape measurement)*
Report: `reports/iPhone7_Landscape_Unity_Report.html` · captures `log/ip7_landscape_unity/` · 17 screens.
Artifact: `3d723260-6e7c-407e-afcc-e42ecd1bf8c0` (label "343 · native-res"; native-resolution
1334×750 screenshot embeds, 2-up grid). Supersedes the earlier `7922f078-…` link, which is
not owned by this account.
Peak diffs: In-Game Menu 47% · Victory·Score 40% · Victory·Best 39% · Choose Look·Surface 37% ·
Choose Look·Cards 35% · Menu·Promo Icons 33%.

**Landscape is markedly less faithful than portrait (peak 47% vs ~17%):**
- 🔴 **In-game menu not adapted to landscape** — the pause tray uses the portrait 2-column
  button grid instead of Obj-C's 3-column landscape layout; every button is repositioned.
- 🔴 **"Dev Panel" debug button ships** on BOTH landscape victory screens (absent in portrait).
- 🟠 **Choose-Look modal mispositioned** — tabs, all swatches, toggle + text offset vs Obj-C.
- Felt renders with different lighting on the right + heavier/rewrapped body text lift the
  baseline diff on every menu screen.

**Correct (no content bugs):** FAQ single first question; Stats markers decorative ✻; promo strip
present; About "▷" divider + version 8.0.0. (A "duplicate ranking for" seen mid-load on the
victory / Last-Score screens is a transient loading frame, not a bug — it settles to "won N".)
