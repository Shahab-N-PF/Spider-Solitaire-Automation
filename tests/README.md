# Functional test suite (Unity build)

The `verify*.py` cases in this directory are **functional UI tests for the Unity
build**. They ask *"does the Unity build work?"* — a different question from the
other suite here:

| Suite | Question | Build |
|---|---|---|
| `verify*.py` + `run_all.py` (this one) | does it **work**? | Unity |
| `compare_unity*.py` | does it **look** like the Obj-C baseline? | Unity vs Obj-C pixels |

The Obj-C build is no longer functionally tested — these cases were converted in
place. `baselines/` still holds the Obj-C reference for the pixel comparison and
must never be re-baselined to Unity (see CLAUDE.md).

> **Before running a `compare_unity*` tool on a fresh clone: you have no Unity
> screenshots yet.** The Obj-C baselines are committed; the Unity captures are not —
> they are shot from the build on the device and land in git-ignored `log/`. Only the
> iPad set is committed (`ipad/unity/`), which is why that one comparison works
> immediately. Run a tool with nothing captured and it exits **2** and tells you where
> the files belong. Full instructions: [`../SETUP.md`](../SETUP.md) →
> *Capturing the Unity screenshots*.

## Why this needs its own driver

Unity renders the whole UI into one opaque view. There is **no accessibility
tree** — Poco sees nothing and WDA reports a single anonymous element — so
element-based automation is unavailable. That leaves pixels.

`compare_unity*.py` drives Unity by **fixed coordinates**, and for a
*pixel-fidelity* tool that is the right call: a comparison must not locate its
targets using the very pixels it is measuring, or a real regression could move a
button and the harness would silently follow it.

Functional testing wants the opposite trade. Here, finding a button by sight is
not cheating — it *is* the assertion. So `unity_ui.py` locates controls with
templates cropped from **Unity's own rendering**, which:

* makes "the Options control is on screen" a real check rather than an assumption;
* taps wherever the control actually is, surviving the between-build layout
  shifts that left `compare_unity.py`'s hardcoded coordinates ~15% off;
* fails loudly (control not found) instead of silently tapping empty felt.

The inherited `assets/` templates are **Obj-C** crops and do not match Unity.
This suite uses `config.UNITY_ASSETS` (`assets_unity/`, per-device) instead.

## Running

```bash
./scripts/wda.sh 00008030-001C51DA0E80A02E     # device UNLOCKED; leave running
export DEVICE_UDID=00008030-001C51DA0E80A02E   # THEN enable Airplane Mode
./.venv/bin/python tests/run_all.py                          # whole suite
./.venv/bin/python tests/run_all.py verifyPlay verifyGamePlay  # a subset
./.venv/bin/python tests/verifyGamePlay.py                   # one test, standalone
```

`run_all.py` preflights the rig (templates present, WDA reachable, `DEVICE_UDID`
set) and exits 2 with a readable message rather than failing test-by-test.

**The suite is destructive.** It ends with `resetStats`, which permanently wipes
local statistics on the device (Game Center scores are untouched). That is safe
where it sits — everything that reads or depends on play history has already run,
and each run re-earns it — but a full run does leave the device's local stats at
zero.

Not in the default suite, on purpose: **`verifyHelpShift.py`** (needs the device
online, which the suite otherwise avoids), **`verifyAds.py`** (same — ads need
the network; see *Ads* below), **`visitLastScore.py`** (its Game Center legs
need the network and a signed-in Apple account), and
**`verifyAdFreeVersion.py`** (the hand-off works offline, but the App Store page
it lands on is the point, and offline that is the same "No Internet Connection"
screen for every link).

## The app is NOT restarted between tests

`helpers.launch_app()` used to create its WDA session with WDA's default
`forceAppLaunch`, which **restarted the app at the start of every test** and
silently threw away in-app state. It now attaches to the running app
(`forceAppLaunch=False`) and only launches when the app is not running.

This is what lets one test build on another: `verifyVictory` uses the Dev Panel
that `openDebugTools` unlocked instead of repeating the 5-tap gesture
(`ui.win_game(level, arm=False)`). A restart hides that button again — verified
both ways on the device.

Two places still want a genuinely fresh app and ask for it explicitly:

* `openDebugTools` → `ui.launch_to_menu(force=True)`. Its premise is that the
  Dev Panel button is hidden until the gesture reveals it, and only a restart
  makes that true — without the force it would fail on a re-run by finding its
  own previous unlock still on screen.
* `ui.cold_launch()` — the recovery path, whose whole job is to discard state.
* `verifyRelaunch` — a whole test built on the restart, and the only one that
  asserts the app comes back on the GAME SCREEN rather than the menu. It presses
  **Home first** (`ui.home()`), then kills the app mid-game and checks the played
  board is restored. That Home press is the whole difference: measured on build
  363, backgrounding then killing brings the game screen back at both a 3.5s and
  a 35s gap, while killing straight from the foreground brings back the **menu**
  — the app writes its state on backgrounding, and no user can kill a foreground
  app anyway. It is deliberately **not in `run_all.py`**: the kill would hide the
  Dev Panel button `verifyVictory` and `verifyDifficultyLevels` depend on.

Consequence for ordering: **`verifyMoreGamesIcons` must stay last** and
`openDebugTools` must stay ahead of `verifyVictory`. See the next section.

## Result (2026-08-13, Unity build 353, iPhone 11, online)

**13/13.** Every test run individually, in suite order, on build 353
(`CFBundleVersion`; the marketing version reads `8.0.0` on every build, so it
cannot tell builds apart — use `tidevice`/`installation.iter_installed`).

There are **no expected failures any more**. `run_all.py`'s `KNOWN_UNITY_GAPS`
is empty.

**Correction — the promo strip is not a port gap.** This README, the test, and
`run_all.py` all used to say the home-screen promo icon strip was dropped by the
Unity port (and, briefly and even more wrongly, that build 353 regressed it).
Both readings were wrong. **The strip only appears once at least one game has
been completed**; on a fresh install with stats at 0 the app does not draw it.
Measured on one device and build with no reinstall between: 0 of 5 icons at
12:07 and 12:11 on a fresh install, 4 of 5 at 12:43 after `verifyVictory` won a
game. That is why the test is **last** in the suite — `verifyVictory` (#12)
satisfies its precondition. Do not move it earlier, and do not file a bug from a
fresh-install capture.

The 5th icon needed a second fix: `promo_freecell` scored ~0.54 against a strip
plainly on screen because **FreeCell's app icon was redesigned** (dark blue
square → lighter squircle with a sparkle). These are other publishers' icons and
will keep changing, so the test now accepts any known art variant
(`promo_freecell_alt.png`; add `<name>_alt.png` when art changes again).

`openDebugTools` was on that list and **is not any more** — the hidden QA entry
point is present on Unity after all. **5 rapid taps on the About screen's spider
emblem** reveal a **"Dev Panel"** button in the bottom-right corner. The earlier
"the gesture opens nothing" reading was a harness fault, not a port gap: the taps
were aimed at the `about_logo` crop, whose centre lands on the *"Spider
SOLITAIRE" wordmark*, and the wordmark is inert. The identical burst ~50 px
higher, on the emblem, works every time. That is why `about_emblem` is now its
own template rather than an offset from the wordmark.

**That button is the cheat route.** Tapping it expands a QA panel — surface /
language / card-back pickers, **Complete Game**, Max Debugger, Kill Banner Ad, PT
Debugger, Screen Stats — so Unity does have the synthetic win the Obj-C build
had. `ui.win_game(level)` drives it end to end (arm on About → deal → Complete
Game → victory), which makes the victory screens reachable without playing a game
out. Complete Game acts on the **active** game, so it does nothing if fired from
About.

Two things still matter for this test to mean anything:

* **The taps must be genuinely rapid.** A loop of ordinary airtest taps runs at
  **~510 ms each** (>2.5 s for five) — outside the detection window — so it would
  report the gesture as absent purely by driving it too slowly. `ui.rapid_tap()`
  sends the whole burst as ONE W3C Actions request executed on-device
  (~70–120 ms/tap) and returns False if it falls back; the test asserts on that
  *before* judging the app, so an inconclusive run never reads as a finding.
* **Fire exactly one burst.** The gesture **toggles** — a second 5-tap burst
  hides the button again. The button is *not* scoped to About (only the gesture
  is); once unlocked it shows on every screen until the app is restarted. The
  test's "hidden beforehand" precondition therefore comes from its own
  `launch_to_menu(force=True)`, and the unlock it leaves behind is deliberate —
  `verifyVictory` uses it.

Everything else passes, including gameplay assertions the Obj-C suite never had:
deal a row from the stock → board changes **9.6%** → undo → residual **0.00%**.

## Coverage

| Test | What it asserts |
|---|---|
| `verifyMainMenu` | all 7 menu controls + logo render *simultaneously* (polled — a launch toast and sparkle can briefly hide one) |
| `verifyStatsPage` | Statistics renders, Game Center present, scrolls end to end to "Reset Statistics" (not tapped) |
| `verifyOptions` | Options opens with Contact Us present, then **four named rows** are *operated*: **Applause Volume** and **Card Lowering** (sliders) each drag to both ends and to mid-track, **Auto Mute Sounds** (ships ON) and **Use Hearts** (ships OFF) each flip and report the new state, and a changed slider value survives leaving the screen and returning. All four are then **reset to fixed values — on failure too** |
| `verifyHelpPage` | Help opens on "Introduction" and the body scrolls to its footer |
| `verifySpiderLogo` | About reachable from both the menu item **and the logo**; version, copyright, links; in-app FAQ opens **and scrolls to its 'submit feedback' footer** |
| `verifyMoreGamesBtn` | the in-app cross-promo page opens, **scrolls** (one swipe, revealing FreeCell + Spiderette below the fold) and returns |
| `verifyMoreGamesIcons` | all 5 promo icons present, **each one opens the App Store**, switching back (never killing the app) returns to the menu, and the 5 go to *different* pages. Needs a completed game first — runs last |
| `openDebugTools` | 5 rapid taps on the About emblem reveal the "Dev Panel" button, bottom-right. Does **not** restart the app (it clears a prior unlock with a toggle-off burst instead), and leaves the button ON for `verifyVictory` and `verifyDifficultyLevels` |
| `verifyChooseLook` | Surface/Cards tabs switch, then the **6th Surface palette** and the **5th Cards palette** are selected and proved to reach the **game table** — the felt and the card backs are read off the table and matched, on *normalised* colour, against the palette that was tapped in that same run. **Puts the default look back** from a `finally`: the menu's three icon controls carry the felt in their crops and drop to 0.62-0.69 against a 0.70 bar on a repainted surface. No "the screen changed" assertion — the selection persists, so that check passes once and fails forever after (standalone, **not in `run_all`**) |
| `verifyPlay` | Play opens the picker, all 5 levels render, Easy deals a **table** |
| `verifyDifficultyLevels` | **Medium…Expert** each deal a game, **win it via the QA cheat**, and leave the victory screen by its own **"back"**; per-level failures reported individually. Needs `openDebugTools`' unlock (re-arms itself if the button has gone). Easy is covered by `verifyPlay` and `verifyVictory`. Every game is completed, so no level raises an abandon prompt — and 4 wins are written to local statistics |
| `verifyFirstLaunch` | a **cold start** (terminate, relaunch) reaches the menu with no pop-ups left on screen; on a fresh install it also clears the two one-per-install gates. Runs **first** |
| `verifyGamePlay` | **deal/undo round trip**, **tap-to-lower** drops the playfield and raises it back, hints respond, all six drawer actions behave, and two Options settings are proved to reach the table — **"Use Hearts"** flips the dealt cards from black spades to red hearts and back, and **"Rich Features"** hides and restores the Timer, Score and Multiplier |
| `resetStats` | reset link + both confirmations, then back to the menu. **DESTRUCTIVE** — wipes local statistics, so it runs **last** |
| `verifyVictory` | wins via the QA cheat (reusing `openDebugTools`' unlock, so it must run after it), then the win screen renders all 7 elements, names the level played, and its own **"back"** returns to the menu — leaving no game in progress |
| `visitLastScore` | the picker's **"LAST SCORE"** opens the ranking view, its header reads **"Last Won Game Score"**, and its forward arrow takes 4 taps (2s apart) — which cycles the period week → month → overall → day → week, a full round trip. Then **"leaderboards"** and **"achievements"** each open Apple's Game Center sheet, headed **"Leaderboards"** / **"Achievements"**, its back arrow leaves that page, and a tap at the bottom dismisses it back to Last Score (online, opt-in) |
| `verifyRelaunch` | one move is played, then the app is **sent to the background and killed on the game screen**, and launched again **~3.5s later and ~35s later** — both times it comes back on the game screen with **the same board**, matched by correlation against the played position (**1.000** on build 363, where a *different* deal scores 0.77-0.79). The second leg carries on with the game the first one restored. Three findings: the Home press is load-bearing (without it the app comes back on the **menu**, because it writes its state on backgrounding), the restored game comes back **paused behind a "tap a card to start"**, and the restored board is **not redrawn pixel-identically** — a per-pixel diff called an identical deal 9-12% changed (standalone, not in `run_all`) |
| `verifyHelpShift` | Contact Us opens the support flow (online, opt-in) |
| `verifyAds` | banner served, interstitial fires on leaving a game, the ad never leaves the app, and the app recovers (online, opt-in) |
| `verifyAdFreeVersion` | About's **"ad free version"** link raises a **No/Yes card** ("Tap Yes to proceed to the App Store"), and answering **Yes** hands off to the App Store — asserted on the foreground **bundle id**, not pixels. Switching back with `ui.resume()` returns to **About**, which is what proves the app was resumed and not restarted. The page it lands on is **Spider Solitaire +**, this game's paid build (online, opt-in) |

### The assertion worth knowing about

Unity publishes no state to read, so "did that control do anything?" is answered
from the screen: capture, act, capture, compare. `verifyGamePlay` uses this for a
real game-logic check:

```
capture board → deal a row from the stock → board must change
              → undo                      → board must return to the original
```

Undo is only correct if the pixels come back. That catches a class of port bug
(undo not restoring state) that no screenshot diff would, and it needs no
accessibility tree.

**"Use Hearts" is the one cross-screen assertion.** Everywhere else the suite
asks "did this control change the board?". This one asks whether a setting on
*another page* changes what the game draws: turn it on in Options, come back, and
the cards on the table already dealt must have gone from black spades to red
hearts — then back again when it is turned off.

It is read by **template**, not by counting red pixels, because the table is
already full of red: every card back and the whole stock pile are red in both
states, and the court cards carry red art either way. Measured inside
`board_box()`:

| table | `card_spade` | `card_heart` |
|---|---|---|
| spades | **1.000** | 0.498 |
| hearts | 0.614 | **1.000** |

Two things to know before touching it. It only works on **Easy, a one-suit
game** — that is what makes "no spades remain" sound, and it would be false on
Medium, which deals spades *and* hearts. And the setting is **persisted**, so the
check normalises a leftover "on" at the start and restores "off" from a
`finally`; the bottom "tap to undo" widget is excluded from the read because it
draws a red heart whatever suit is in play.

**"Rich Features" is read as ink present or absent**, and both of the other
techniques on this page are wrong for it. There is nothing stable to
template-match — the timer ticks every second, the score moves as you play, the
multiplier is per level. And a before/after **pixel diff proves nothing**,
because the running timer changes that strip every second on its own; it would
pass with the setting dead.

So the check measures how much of the Timer/Score/Multiplier box is ink rather
than background, against the box's **own median colour** so a Choose Look surface
change cannot move the threshold. Measured on build 363: **~12–17% with the
setting on, 0.00% with it off**, and bare felt anywhere on the table also reads
0.00% — there is no floor to fight.

The box is anchored to the "tap to lower" caption and located **once, while the
setting is still on**. That is required, not defensive: the caption is itself one
of the things Rich Features hides. The test reports that (and the top bar's score
counter) as an observation rather than a failure — "tap to undo" and "tap for
hints" survive. It also means a run that left the setting OFF would leave
`check_lower()` with no caption to find, which is why the restore runs from a
`finally`.

**"tap to lower" is read from a position, not a pixel diff.** It slides the whole
playfield down the screen, so the top bar's `back` control *is* the state
read-out — y=160 raised, y=232 lowered on the iPhone 11, repeatably to the pixel.
Asserting on that is exact and it says what actually happened ("the playfield
dropped 72 px"), where a diff percentage only says "something changed".

Two things about that control are worth knowing before touching it:

* **It is a persistent setting, not per-game state.** It survives leaving the
  game and dealing another. A run that dies with the view down leaves it down for
  every run after it — and with the view down, a blind coordinate misses the
  moved stock pile, so the *next* run fails at the deal step with a message about
  the stock, a mile from the cause. `ui.tap_stock()`'s fallback is therefore
  anchored to the top bar, and `check_lower()` raises the view before either
  assertion can throw. The check itself is **exactly two taps — lower, then
  raise**; the starting state is read from the bar's position rather than probed
  with a tap, so nothing is done twice just to find out where we are. A third tap
  happens only in recovery, when a previous run left the view down, and it says
  so on the line.
* **The bottom captions vanish for ~4.5s** while the view slides, and when they
  come back in the *lowered* state `tap_lower` only scores 0.72-0.74 against the
  0.70 threshold. So the control is located once, while raised, and the same
  point is tapped twice — it does not move between the two layouts.

`verifyOptions` pushes the same idea further. A settings control does not just
*respond*, it *holds a value* — and on Unity that value is readable, because the
knob's position **is** the setting:

```
toggle   knob left = off, knob right = on     (pill 602-734 px at 828 wide)
slider   knob anywhere along the track        (track 513-757 px)
```

So the assertion is not "the picture changed after I tapped" — which an
animation, an ad or a scroll would also satisfy — but *"it read ON, I tapped it,
it now reads OFF, I tapped again and it reads ON"*. Both toggle directions get
covered by driving one row that ships ON (Auto Mute Sounds) and one that ships
OFF (Use Hearts). Each slider is dragged to both ends and to mid-track, and then
a changed value is checked to survive leaving the screen and returning — the bit
that says the setting was *applied*, not merely drawn.

The four rows it drives are named in `TARGETS`, listed in **page order** so the
run is one downward sweep: `ui.opt_row()` has to rewind to the top whenever a
row has already scrolled past, which is the expensive path.

**Every run ends with those four at fixed values** — Applause Volume ~0.5, Auto
Mute Sounds ON, Card Lowering ~0.5, Use Hearts OFF — and the reset runs from a
`finally`, so it happens *on failure too*. That matters more than it sounds:
every check ends in an assertion that raises, so without it a failed run strands
a toggle flipped or a slider at maximum for the next test and the next run to
inherit. Fixed targets rather than "put back what was found" also mean each run
*starts* from a known state, whatever the last one — or a person poking at the
phone — left behind. The reset never raises; anything it cannot set it names on
stdout, and that only fails the test when the run was otherwise passing.

**Why `MID_TOL` is 0.08 and not tighter.** A drag asking these sliders to move
less than about **14 px — roughly 0.06 of the track — does not register as a
drag at all**: the knob moves by 0.000, at swipe durations of 0.5 s, 1.2 s and
2.0 s alike. That is a gesture-recognition floor, not a slider step, and it means
no gesture can close a gap smaller than itself. `ui.slider_set()` therefore
answers a too-short correction by parking the knob at the far end and
re-approaching, rather than re-issuing a gesture that cannot move anything —
which is what it used to do, three times over, before reporting the value as if
the control had refused. Both ends still land **exactly** (0.00 / 1.00).

Two things measured while building it, both worth not re-deriving:

* **The "−" and "+" beside a slider are not buttons.** They label the ends of the
  track. 36 points swept across a grid over both glyphs, 3 taps each, plus a 2 s
  press-and-hold, plus taps on the track either side of the knob: the value never
  moved and the whole-screen diff was **0.00000**. Dragging the knob is a
  slider's only interaction — which is also what the row's own caption says
  ("Move slider to change the volume").
* **The app saves settings when it goes to the BACKGROUND, not on every change.**
  So `cold_launch()` is a misleading way to test persistence: it kills the app
  from the foreground, which no real user can do (the switcher backgrounds an app
  before you can swipe it away). Change → Home → kill → relaunch **keeps** the
  value; change → kill straight from the foreground **loses** it. Read on its own
  that second result looks exactly like "the Unity port stopped saving settings".

## Templates and their quality gate

| Path | Purpose |
|---|---|
| `unity_ui.py` (repo root) | the driver: matching, navigation, dialogs, table controls, pixel observation |
| `assets_unity/` | **the** Unity template set — one set for every 19.5:9 phone |
| `iphone14/assets_unity/` | reference crops at 1290px; no longer used at runtime |
| `scripts/capture_unity_screens.py` | bootstrap: walk Unity by coordinate, shoot every screen → `log/unity_screens/` |
| `scripts/crop_unity_assets.py` | cut anchors out of those captures (`--device iphone14｜iphone11`) |
| `scripts/derive_unity_assets.py` | derive one device's templates from another's by multi-scale matching |
| `scripts/verify_unity_assets.py` | offline quality gate: fragile / ambiguous crops |
| `scripts/verify_unity_scaling.py` | offline gate: does the one set cover every device? |

### One set, every device

There is no per-device Unity template tree. `unity_ui.find()` rescales each crop
for the attached phone, so an iPhone 16 Pro needs **no new templates and no new
coordinates** — everything resolution-dependent in the suite is already a
fraction of `screen_size()`, read from the device at runtime. Verified by running
the whole suite on one: **12/13 on an iPhone 16 Pro (1206×2622)**, the only
failure the promo strip — which was later shown not to be a gap at all: that
device had no completed game, which is what the strip needs (see the result
section above).

**Two rendering regimes, not one.** Unity's own artwork scales by **width**
(1206/828 = 1.4565 on a 16 Pro). Spider's confirmation dialogs are **native iOS
alerts** — SF font, translucent card, system button pills — and native UI is laid
out in *points*, so it scales by **point density** instead (@2x → @3x = 3/2 =
1.500). Only 3% apart, and that 3% is the difference between working and not:
`prompt_abandon` peaked at 0.962 @1.500 but only 0.694 inside the width-based
sweep, so the abandon prompt went unrecognised, was answered "No", and **every
game-dealing test failed**. `NATIVE_UI` in `unity_ui.py` lists the templates on
the point-density basis; everything else uses width.

That is measured, not assumed. Cross-matching every template between an iPhone 11
(828) and an iPhone 14 Pro Max (1290) capture of the same screen:

| direction | result | best scale | predicted |
|---|---|---|---|
| 1290 → 828 (downscale) | 49/49 ≥0.80, median **0.978** | 0.645 (sd 0.003) | 0.642 |
| 828 → 1290 (upscale) | 53/53 ≥0.80, median **0.981** | 1.560 (sd 0.005) | 1.558 |

The scales cluster within ~0.5% of the pure width ratio, which is why `find()`
sweeps a narrow band around the prediction rather than trusting it outright. It
tries the predicted scale first and exits early, so the common case still costs a
single `matchTemplate`.

**Keep that sweep tight.** Every extra scale is another chance for the *wrong*
screen to cross the threshold, and that is not hypothetical — a first cut used
±3% and the top bar's "menu" word (`in_game_menu`) started matching the Stats
and Help pages, which it scores only 0.684 / 0.659 against at native scale:

| sweep | false matches across 5 weak screens |
|---|---|
| ±3% | 3 (0.759, 0.712, 0.760) |
| ±1% | 1 (0.704) |
| single scale | 0 |

±1% is still 2–3× the observed prediction error, so it buys tolerance without
widening the door. The remaining case was a genuinely weak anchor rather than a
scaling problem: `in_game_menu` is **shared chrome** — the same "menu" word sits
on the Stats page, the Help page and the victory screen — so it now carries
`THRESH["in_game_menu"] = 0.85`. True matches score 0.98–1.00 and the highest
false is 0.827, a clean gap. That also fixed a pre-existing bug: at the default
0.70, `at_table()` returned True on the **victory screen**, reporting a game in
progress right after a win.

`verify_unity_scaling.py` keeps this honest by driving the **real** `find()`
against saved captures per device, and reports the two failures separately — a
MISS means the one-set design does not reach that device, a GHOST means a crop is
ambiguous. Current, with `--ghosts --synthetic`:

| profile | unity scale | native scale | missed | ghosts |
|---|---|---|---|---|
| iPhone 11 (828×1792, @2x) | 1.000 | 1.000 | 0 | 0 |
| iPhone 14 Pro Max (1290×2796, @3x) | 1.558 | 1.500 | 0 | 0 |
| iPhone 16 Pro (1206×2622, @3x) | 1.457 | 1.500 | 0 | 0 |

All three are **real captures** — the iPhone 16 Pro profile was synthetic
(a resampled iPhone 14 frame) until the device was available; it is now that
device's own screens. Profiles judge different template counts because not every
screen has been captured on every phone.

**Limits worth stating.** The iPhone 16 Pro profile is *synthetic* — a resampled
iPhone 14 capture. It proves the scaling math, not how that device actually
renders; confirm on the real phone when one is attached. And the **iPhone 7**
(750×1334, 16:9) is out of scope for this: its UI genuinely reflows rather than
scaling, so it would need its own set via `UNITY_ASSETS`. The status-bar airplane
glyph in `preflight_offline.py` also stays per-device — it is an iOS element, not
Unity's.

A suite that locates by template is only as good as its templates, so
`verify_unity_assets.py` checks both ways one can be bad, with **no device**:

* **FRAGILE** — matches its own source frame but not *another* capture of the
  same screen. The menu labels sit under an animated sparkle, so a crop that
  caught one can score 1.000 on its source and nothing else. Every template is
  tested against the same screen captured from a **different build** (341 vs 343).
* **AMBIGUOUS** — also matches a screen it shouldn't, which would let an
  assertion pass on the wrong screen.

Currently **54 templates, 0 fragile, 0 ambiguous**. Two findings from this gate
are baked into the driver: the menu labels stay visible **behind the Choose Look
modal** (so `ui.on_menu()` rules the modal out), and the Help footer carries the
**same** FAQ link as About.

The FAQ page shares a footer link too — its bottom carries the **same 'submit
feedback' link** as About (`about_feedback`), which is what `verifySpiderLogo`
scrolls to in order to prove the FAQ's whole body rendered. Like the Help/About
FAQ link, this is a real shared element, not a template fault.

Refreshing templates for a new Unity build (**not** the same as re-baselining —
`baselines/` stay Obj-C):

```bash
./.venv/bin/python scripts/capture_unity_screens.py
./.venv/bin/python scripts/crop_unity_assets.py --device iphone11
./.venv/bin/python scripts/verify_unity_assets.py      # gate before trusting
```

## Gotchas

* **Pin the device with `DEVICE_UDID`.** Airtest picks the *first* device it can
  see, including **WiFi-paired** ones that aren't plugged in — the iPhone 7 pairs
  over WiFi and outranked the USB iPhone 11, so a run aimed at the 11 silently
  drove the 7 (`wda xctest launched but check failed`). `idevice_id -l` won't
  show the culprit (USB only); `tidevice list` does, with a `ConnType` column.
* **Run OFFLINE (Airplane Mode), and start WDA first.** Online, FingerArts pops
  full-screen cross-promo interstitials on screen transitions, and one fires
  *reliably*: opening Options from the in-game drawer was interrupted on 3/3
  attempts. A blind tap on one can land on the ad body and open a **StoreKit App
  Store sheet**. `ui.lost()` detects "nothing we recognise is on screen" and
  `ui.recover()` terminates and relaunches rather than hunting for a close button
  whose position moves with the ad creative. Order matters: WDA needs the network
  for its certificate check at launch, but runs over USB afterwards.
* **Two look-alike dialogs, opposite answers.** "Are you sure you want to abandon
  the currently paused game?" → **Yes**; "Would you like to review the game rules
  before to play?" → **No**. Same geometry, so they are told apart by TEXT, never
  by position — and the text now comes from **WDA**, not from image matching.
* **Do not match iOS alerts as images.** They are translucent, so a crop bakes in
  whatever was behind the alert when it was cut. With the abandon prompt plainly
  on screen, and the crops taken from that very device, `prompt_abandon` scored
  **0.188**, `dialog_yes` 0.311, `dialog_no` 0.329 — all far under 0.70 — purely
  because the templates were cut over the game table and this one sat over the
  difficulty picker. `settle_prompts()` silently saw nothing, the deal was
  cancelled, and `verifyPlay` failed. These are real `UIAlertController`s, so
  `ui.alert_now()` reads their text over WDA and `ui.answer_dialog()` presses
  Yes/No by name; the templates remain only as a fallback.
* **Two first-launch gates block everything: Terms & Conditions, then ATT.**
  Both are matched as **images** — *neither* is visible to WDA, and the earlier
  claim here that T&C was matched by alert text was wrong. Measured on build 363
  with a live session while the T&C pop-up was plainly on screen, `/alert/text`
  returned `""` and `/alert/buttons` `[]`: the app draws it rather than presenting
  a `UIAlertController`. That branch therefore never fired and the gate was never
  dismissed — dead code nobody noticed, because no test cold-launched until
  `verifyFirstLaunch` was added to the suite. ATT is invisible for a different
  reason: it is presented out of process, so `/alert/text` 404s on it.
  `ui.clear_overlays()` taps `tc_continue`, then **`att_allow`** — the app wants
  tracking *granted* before it lets a first launch through, and answering "Ask
  App Not to Track" does not clear the gate (`att_deny` is kept for reference).
  It still only touches alerts it positively recognises as gates, so the game's
  own confirmations are left to `settle_prompts()`.
* **They come back far more often than "once per install".** The app writes its
  state when it goes to the **background**, and `cold_launch()` terminates it
  from the **foreground**, so the "agreed" flag can be lost and both reappear on
  the next launch. `cold_launch()` therefore sweeps, waits, and sweeps again: the
  gates arrive in sequence, so one immediate pass can clear T&C and return before
  ATT has even been drawn.
* **`/alert/buttons` does not exist on this WDA (15.0.0) — it 404s.** That made
  `helpers.alert_buttons()` return `[]`, which `clear_overlays()` read as "no
  alert", so the whole overlay sweep was dead code. Use `helpers.alert_text()` as
  the presence check; `[]` from `alert_buttons()` means nothing either way.
* **A third dialog isn't Yes/No at all.** A "Did you know?" tip pops over the
  table after a deal with **OK / Show Me**, and blocks taps on everything beneath
  it until answered — it silently swallowed a tap whose template had matched
  fine. `settle_prompts()` checks it first and answers **OK** ("Show Me"
  navigates away to Options).
* **…and it cannot be template-matched, which cost two levels.** The `prompt_tip`
  / `tip_ok` crops were cut from a rendering where the card was **dark green with
  white text**; this build draws it **pale mint with black text**. Against
  captures where the tip was plainly on screen they scored **0.344** and
  **0.397** against a 0.70 bar, so the tip branch never fired and the card sat
  there swallowing the cheat taps — reported as "the cheat did not lead to the
  victory screen" on **2 of 4** levels, a long way from the cause. The crops are
  gone. `ui.card_dialog()` finds the card by **shape** — a large, solid,
  uniformly bright rounded rect — and `ui.card_buttons()` reads its pills, both
  measured against the picture's own colours so a repainted surface is
  irrelevant. It handles the **one-button and two-button** forms without being
  told which to expect, and the **reset-scores** prompt is the same widget.
* **The Dev Panel overlay hides the menu.** Once expanded it follows you across
  screens and covers the right-hand column — which is where the main menu draws
  its labels, so `ui.on_menu()`/`ui.to_menu()` cannot confirm the menu while it
  is up. Navigate around it or call `ui.close_dev_panel()` first.
* **Some feedback is transient.** The hint highlight plays for <0.7 s and the
  board returns to *exactly* its previous pixels, so a single capture after a
  settle reads as "the control did nothing". Use `ui.peak_change_after()` to
  sample across the animation. An earlier version of this test reported a false
  Unity defect this way.
* **A screenshot cannot tell you which app you are looking at.** Use
  `ui.active_app()` (WDA's foreground bundle id) for anything that hands off to
  another app, and `ui.resume()` to come back — it foregrounds Spider WITHOUT
  restarting it, so in-app state survives. Never terminate to get back.

## Ads (`verifyAds.py`) — online only

The rest of the suite runs offline to keep ads *out*. This one test runs online
to check they are still there, because ads are revenue and a port that broke
them is a regression nothing else here would see.

Hard assertions: a banner is served on the menu; an interstitial appears where
the app schedules one (leaving a game — fired on **12 of 12** attempts); the ad
never moves the user out of Spider on its own; the app is usable afterwards.
Whether the ad could be *closed* is reported, not asserted — creatives are third
party and differ every run, so failing on one creative's close button would make
the suite flaky.

What it found on build 353, and why the test is shaped this way:

* Interstitials **chain**. A video plays ~15 s, then at ~16 s it opens an App
  Store product sheet **by itself** — confirmed with screenshot-only sampling,
  40 frames, no touch events of any kind — and closing that sheet starts a
  further playable ad.
* **The chain is long.** Watched for a full 5 minutes: exactly one closable
  control ever appeared (the store sheet's X, at t+27 s) and Spider's own UI
  never came back. A user, who has no relaunch button, is stuck for minutes.
  Worth raising with whoever owns the ad configuration.
* The only other exit is a small **"▶▶" skip glyph**, which the driver
  deliberately does **not** use: its position moves between creatives (top-left
  on some, top-right on others) and a crop of it scores 0.65–0.75 on real ads but
  **0.656 on the plain main menu** — indistinguishable from noise. Guessing at it
  would tap the ad and open the App Store.
* `ui.dismiss_ad()` was **dead on Unity**: it only looked for an `ad_close` crop
  that exists in the Obj-C `assets/` set, and `have()` searches the Unity set, so
  it always returned False. It now also knows `ad_store_close` — the X on the
  in-app StoreKit sheet, which sits on plain white and matches cleanly (1.000 on
  the sheet, ≤0.29 on all eight Spider screens). `ui.ad_free(budget)` loops
  close-or-wait and gives up honestly rather than pretending.
